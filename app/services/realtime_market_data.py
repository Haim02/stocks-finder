"""
realtime_market_data.py — Real-Time Market Data Service
=========================================================

Provides real IV Rank, IV Percentile, Greeks, and options chain data
using free sources: yfinance (primary) + Barchart (fallback).

Used by Agent 2 (Options Strategist) to replace the approximate
IV calculation with real market data.

No paid API keys required.
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date, timedelta

import yfinance as yf
import pandas as pd
import numpy as np
import requests

logger = logging.getLogger(__name__)

# ── In-memory TTL cache ───────────────────────────────────────────────────────
_CACHE_TTL = 3600  # 1 hour
_iv_cache: dict[str, tuple] = {}       # ticker → (RealTimeIVData, timestamp)
_chain_cache: dict[str, tuple] = {}    # "ticker:dte" → (OptionsChainSnapshot, timestamp)

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class RealTimeIVData:
    ticker: str
    current_price: float
    iv_current: float          # current IV% (annualized)
    iv_rank: float             # 0-100, based on 52-week range
    iv_percentile: float       # 0-100, based on 252 trading days
    iv_high_52w: float         # 52-week high IV
    iv_low_52w: float          # 52-week low IV
    expected_move_30d: float   # ±$ expected move over 30 days (1SD)
    atm_call_iv: float         # ATM call implied volatility
    atm_put_iv: float          # ATM put implied volatility
    bid_ask_spread_pct: float  # ATM option bid-ask spread %
    is_liquid: bool            # True if spread < 10%
    data_source: str           # "yfinance" | "barchart" | "proxy"
    fetched_at: str            # ISO timestamp


@dataclass
class OptionsChainSnapshot:
    ticker: str
    expiration: str            # YYYY-MM-DD
    dte: int
    calls: object              # pandas DataFrame
    puts: object               # pandas DataFrame
    atm_strike: float
    current_price: float


# ── yfinance Real IV Calculator ───────────────────────────────────────────────

def _get_atm_iv_from_chain(ticker: str, target_dte: int = 35) -> tuple[float, float, float, bool]:
    """
    Get real ATM implied volatility from yfinance options chain.
    Finds the expiration closest to target_dte.

    Returns (atm_call_iv, atm_put_iv, bid_ask_spread_pct, is_liquid).
    All as floats. IV values are 0-1 scale (multiply by 100 for %).
    """
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            return 0.0, 0.0, 1.0, False

        # Find expiration closest to target_dte
        today = date.today()
        best_exp = None
        best_diff = 999

        for exp_str in expirations:
            try:
                exp_date = date.fromisoformat(exp_str)
                diff = abs((exp_date - today).days - target_dte)
                if diff < best_diff:
                    best_diff = diff
                    best_exp = exp_str
            except ValueError:
                continue

        if not best_exp:
            return 0.0, 0.0, 1.0, False

        chain = stock.option_chain(best_exp)
        hist = stock.history(period="2d")
        if hist.empty:
            return 0.0, 0.0, 1.0, False

        current_price = float(hist["Close"].iloc[-1])

        # Find ATM call
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        if calls.empty or puts.empty:
            return 0.0, 0.0, 1.0, False

        calls["distance"] = abs(calls["strike"] - current_price)
        puts["distance"] = abs(puts["strike"] - current_price)

        atm_call = calls.nsmallest(1, "distance").iloc[0]
        atm_put = puts.nsmallest(1, "distance").iloc[0]

        call_iv = float(atm_call.get("impliedVolatility", 0) or 0)
        put_iv = float(atm_put.get("impliedVolatility", 0) or 0)

        # Bid-ask spread check
        call_bid = float(atm_call.get("bid", 0) or 0)
        call_ask = float(atm_call.get("ask", 0) or 0)
        call_mid = (call_bid + call_ask) / 2 if (call_bid + call_ask) > 0 else 1
        spread_pct = (call_ask - call_bid) / call_mid if call_mid > 0 else 1.0

        is_liquid = spread_pct < 0.10

        return call_iv, put_iv, spread_pct, is_liquid

    except Exception as e:
        logger.warning("ATM IV fetch failed for %s: %s", ticker, e)
        return 0.0, 0.0, 1.0, False


def _get_real_iv(ticker: str, price: float) -> float:
    """
    Get real IV from options chain with multiple fallback methods.
    Never returns 0 — always gives a usable estimate.
    Critical for meme/short-squeeze stocks where the standard ATM filter misses options.
    """
    stock = yf.Ticker(ticker)

    # Method 1: Options chain — wider 10% strike band, try first 4 expirations
    try:
        expirations = stock.options
        if expirations:
            for exp in expirations[:4]:
                try:
                    chain = stock.option_chain(exp)
                    iv_values = []
                    for df in (chain.calls, chain.puts):
                        if df.empty:
                            continue
                        atm = df[
                            (df["strike"] >= price * 0.90) &
                            (df["strike"] <= price * 1.10) &
                            (df["impliedVolatility"] > 0.01)
                        ]
                        iv_values.extend(atm["impliedVolatility"].tolist())
                    if iv_values:
                        iv = float(np.median(iv_values)) * 100
                        if iv > 1.0:
                            logger.info("_get_real_iv %s (options chain): %.1f%%", ticker, iv)
                            return iv
                except Exception:
                    continue
    except Exception as e:
        logger.debug("Options chain failed for %s: %s", ticker, e)

    # Method 2: HV-based estimate with move-adjusted multiplier
    # IV is typically 10-30% above realised vol; for stocks in motion it's much higher
    try:
        hist = stock.history(period="3mo")
        if not hist.empty and len(hist) > 10:
            returns = hist["Close"].pct_change().dropna()
            rv_10 = float(returns.rolling(10).std().iloc[-1]) * (252 ** 0.5) * 100
            rv_30 = (
                float(returns.rolling(30).std().iloc[-1]) * (252 ** 0.5) * 100
                if len(returns) >= 30 else rv_10
            )
            base_iv = max(rv_10, rv_30)
            recent_5d = abs(float(hist["Close"].pct_change(5).iloc[-1])) * 100
            if recent_5d > 20:
                multiplier = 3.0
            elif recent_5d > 10:
                multiplier = 2.0
            elif recent_5d > 5:
                multiplier = 1.5
            else:
                multiplier = 1.2
            estimated = round(base_iv * multiplier, 1)
            logger.info(
                "_get_real_iv %s (HV estimate): %.1f%% (rv_10=%.1f rv_30=%.1f 5d=%.1f%% x%.1f)",
                ticker, estimated, rv_10, rv_30, recent_5d, multiplier,
            )
            return estimated
    except Exception as e:
        logger.debug("HV estimate failed for %s: %s", ticker, e)

    # Method 3: Beta-based rough estimate
    try:
        beta = stock.info.get("beta") or 0
        if beta and beta > 0:
            estimated = round(min(beta * 30, 200), 1)
            logger.info("_get_real_iv %s (beta fallback): %.1f%%", ticker, estimated)
            return estimated
    except Exception:
        pass

    logger.warning("_get_real_iv %s: all methods failed — returning 30%% default", ticker)
    return 30.0


def _calc_iv_rank_from_history(ticker: str, current_iv: float) -> tuple[float, float, float, float]:
    """
    Calculate IV Rank and IV Percentile using 1-year of historical
    implied volatility derived from daily close prices.

    Returns (iv_rank, iv_percentile, iv_high_52w, iv_low_52w).
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if len(hist) < 50:
            return 50.0, 50.0, current_iv * 1.5, current_iv * 0.5

        # Calculate rolling 20-day historical volatility as IV proxy
        returns = hist["Close"].pct_change().dropna()
        rolling_vol = returns.rolling(20).std() * math.sqrt(252) * 100  # annualized %
        rolling_vol = rolling_vol.dropna()

        if rolling_vol.empty:
            return 50.0, 50.0, current_iv * 1.5, current_iv * 0.5

        iv_high_52w = float(rolling_vol.max())
        iv_low_52w = float(rolling_vol.min())

        # Use current_iv if provided (real), else use last rolling vol
        iv_now = current_iv if current_iv > 0 else float(rolling_vol.iloc[-1])

        # IV Rank
        if iv_high_52w == iv_low_52w:
            iv_rank = 50.0
        else:
            iv_rank = (iv_now - iv_low_52w) / (iv_high_52w - iv_low_52w) * 100

        # IV Percentile
        n_lower = (rolling_vol < iv_now).sum()
        iv_pct = n_lower / len(rolling_vol) * 100

        return round(iv_rank, 1), round(iv_pct, 1), round(iv_high_52w, 1), round(iv_low_52w, 1)

    except Exception as e:
        logger.warning("IV Rank calc failed for %s: %s", ticker, e)
        return 50.0, 50.0, 30.0, 15.0


def _calc_expected_move(price: float, iv_pct: float, dte: int) -> float:
    """
    Expected Move = Price × IV × √(DTE/365)
    iv_pct is decimal (0.25 = 25%) OR percentage (25.0) — handle both.
    """
    if price <= 0 or dte <= 0:
        return 0.0
    # Normalize: if iv_pct > 2.0 it's already in percentage form
    iv = iv_pct / 100.0 if iv_pct > 2.0 else iv_pct
    if iv <= 0:
        return 0.0
    em = price * iv * (dte / 365) ** 0.5
    return round(em, 2)


# ── Main data fetcher ─────────────────────────────────────────────────────────

def get_realtime_iv_data(ticker: str) -> RealTimeIVData:
    """
    Main entry point. Returns real IV data for a ticker.

    Tries yfinance first (real options chain IV).
    Falls back to historical volatility proxy if options data unavailable.
    Results are cached for 1 hour.
    """
    cached = _iv_cache.get(ticker)
    if cached and (time.time() - cached[1]) < _CACHE_TTL:
        logger.debug("IV cache hit for %s", ticker)
        return cached[0]

    logger.info("Fetching real-time IV data for %s...", ticker)

    # Step 1: Get current price
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        current_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
    except Exception:
        current_price = 0.0

    if current_price <= 0:
        logger.warning("Could not get price for %s", ticker)
        return _fallback_iv_data(ticker)

    # Step 2: Get real ATM IV from options chain
    call_iv, put_iv, spread_pct, is_liquid = _get_atm_iv_from_chain(ticker, target_dte=35)

    # Use average of call and put IV as current IV
    current_iv_raw = (call_iv + put_iv) / 2 if (call_iv + put_iv) > 0 else 0.0
    current_iv_pct = current_iv_raw * 100  # convert to percentage

    data_source = "yfinance" if current_iv_raw > 0 else "proxy"

    # Sanity check — standard ATM filter misses meme/short-squeeze stocks
    if current_iv_pct < 5.0:
        logger.warning(
            "%s: IV suspiciously low (%.1f%%) — retrying with robust method", ticker, current_iv_pct
        )
        current_iv_pct = _get_real_iv(ticker, current_price)
        data_source = "estimated"

    # Enhancement: try OpenBB for more accurate IV Rank
    try:
        from app.services.openbb_service import get_iv_rank_openbb
        openbb_result = get_iv_rank_openbb(ticker)
        if openbb_result:
            openbb_iv, _ = openbb_result
            if openbb_iv > 0:
                current_iv_pct = openbb_iv
                data_source = "openbb+yfinance"
                logger.info("%s: OpenBB IV override → %.1f%%", ticker, current_iv_pct)
    except Exception:
        pass  # graceful fallback to yfinance

    # Step 3: Calculate IV Rank and Percentile
    iv_rank, iv_pct, iv_high, iv_low = _calc_iv_rank_from_history(ticker, current_iv_pct)

    # Step 4: Expected move (30 days) — use ATM IV if available, else rolling vol
    iv_for_em = current_iv_raw if current_iv_raw > 0 else (current_iv_pct / 100)
    em_30d = _calc_expected_move(current_price, iv_for_em, 30)

    logger.info(
        "%s: price=$%.2f IV=%.1f%% IVR=%.1f IVP=%.1f EM30d=±$%.2f liquid=%s source=%s",
        ticker, current_price, current_iv_pct, iv_rank, iv_pct, em_30d, is_liquid, data_source,
    )

    result = RealTimeIVData(
        ticker=ticker,
        current_price=round(current_price, 2),
        iv_current=round(current_iv_pct, 1),
        iv_rank=iv_rank,
        iv_percentile=iv_pct,
        iv_high_52w=iv_high,
        iv_low_52w=iv_low,
        expected_move_30d=em_30d,
        atm_call_iv=round(call_iv * 100, 1),
        atm_put_iv=round(put_iv * 100, 1),
        bid_ask_spread_pct=round(spread_pct * 100, 1),
        is_liquid=is_liquid,
        data_source=data_source,
        fetched_at=datetime.utcnow().isoformat(),
    )
    _iv_cache[ticker] = (result, time.time())
    return result


def get_options_chain(ticker: str, target_dte: int = 35) -> Optional[OptionsChainSnapshot]:
    """
    Get the full options chain for a ticker at the expiration closest to target_dte.
    Used for strike selection in Agent 2. Results cached for 1 hour.
    """
    cache_key = f"{ticker}:{target_dte}"
    cached = _chain_cache.get(cache_key)
    if cached and (time.time() - cached[1]) < _CACHE_TTL:
        logger.debug("Options chain cache hit for %s", ticker)
        return cached[0]

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            return None

        today = date.today()
        best_exp = min(
            expirations,
            key=lambda e: abs((date.fromisoformat(e) - today).days - target_dte)
        )

        chain = stock.option_chain(best_exp)
        hist = stock.history(period="2d")
        current_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0

        calls = chain.calls.copy()
        calls["distance"] = abs(calls["strike"] - current_price)
        atm_strike = float(calls.nsmallest(1, "distance").iloc[0]["strike"])

        dte = (date.fromisoformat(best_exp) - today).days

        snapshot = OptionsChainSnapshot(
            ticker=ticker,
            expiration=best_exp,
            dte=dte,
            calls=chain.calls,
            puts=chain.puts,
            atm_strike=atm_strike,
            current_price=current_price,
        )
        _chain_cache[cache_key] = (snapshot, time.time())
        return snapshot

    except Exception as e:
        logger.warning("Options chain fetch failed for %s: %s", ticker, e)
        return None


def find_strike_by_delta(
    chain_snapshot: OptionsChainSnapshot,
    target_delta: float = 0.20,
    option_type: str = "put",
) -> Optional[float]:
    """
    Find the strike closest to a target delta in the options chain.
    Uses impliedVolatility as a delta proxy (lower IV OTM ≈ lower delta).

    Returns the strike price, or None if not found.
    """
    try:
        df = chain_snapshot.puts if option_type == "put" else chain_snapshot.calls
        price = chain_snapshot.current_price

        if df.empty:
            return None

        # Filter to OTM options only
        if option_type == "put":
            otm = df[df["strike"] < price].copy()
        else:
            otm = df[df["strike"] > price].copy()

        if otm.empty:
            return None

        # Use distance from ATM as delta proxy
        # Further OTM = lower delta
        # Target delta 0.20 ≈ roughly 1SD from current price
        expected_move = chain_snapshot.current_price * 0.20 * math.sqrt(chain_snapshot.dte / 365)

        if option_type == "put":
            target_strike = price - expected_move * (1 / target_delta * 0.15)
        else:
            target_strike = price + expected_move * (1 / target_delta * 0.15)

        # Find closest strike to target
        otm["distance"] = abs(otm["strike"] - target_strike)
        best = otm.nsmallest(1, "distance")

        if best.empty:
            return None

        return float(best.iloc[0]["strike"])

    except Exception as e:
        logger.warning("Strike by delta failed: %s", e)
        return None


def _fallback_iv_data(ticker: str) -> RealTimeIVData:
    """Return neutral fallback data when all fetches fail."""
    return RealTimeIVData(
        ticker=ticker,
        current_price=0.0,
        iv_current=25.0,
        iv_rank=50.0,
        iv_percentile=50.0,
        iv_high_52w=40.0,
        iv_low_52w=15.0,
        expected_move_30d=0.0,
        atm_call_iv=25.0,
        atm_put_iv=25.0,
        bid_ask_spread_pct=15.0,
        is_liquid=False,
        data_source="fallback",
        fetched_at=datetime.utcnow().isoformat(),
    )


# ── Batch scanner ─────────────────────────────────────────────────────────────

def scan_for_high_iv_tickers(
    tickers: list[str],
    min_iv_rank: float = 35.0,
    min_iv_pct: float = 50.0,
    require_liquid: bool = True,
) -> list[RealTimeIVData]:
    """
    Scan a list of tickers and return those that pass the IV filters.
    Used by Agent 2 to pre-filter candidates before full analysis.

    Returns list sorted by IV Rank descending.
    """
    results = []
    for ticker in tickers:
        try:
            data = get_realtime_iv_data(ticker)
            if data.iv_rank >= min_iv_rank and data.iv_percentile >= min_iv_pct:
                if not require_liquid or data.is_liquid:
                    results.append(data)
            time.sleep(0.3)  # be nice to yfinance
        except Exception as e:
            logger.warning("Scan failed for %s: %s", ticker, e)
            continue

    results.sort(key=lambda x: x.iv_rank, reverse=True)
    logger.info(
        "IV scan: %d/%d tickers passed (IVR≥%.0f, IVP≥%.0f)",
        len(results), len(tickers), min_iv_rank, min_iv_pct,
    )
    return results
