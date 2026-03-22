"""
IV Rank, VIX, and earnings calendar utilities.
Used by OptionsStrategyEngine to determine IV environment.
"""
import logging
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)


def get_current_iv(ticker: str) -> float:
    """Return ATM implied volatility for the nearest expiry. Fallback: 0.30."""
    try:
        stock    = yf.Ticker(ticker)
        expiries = stock.options
        if not expiries:
            return 0.30
        chain = stock.option_chain(expiries[0])
        try:
            price = stock.fast_info.last_price
        except Exception:
            price = float(stock.history(period="1d")["Close"].iloc[-1])

        calls = chain.calls.copy()
        calls["dist"] = (calls["strike"] - price).abs()
        atm_call = calls.sort_values("dist").iloc[0]

        puts = chain.puts.copy()
        puts["dist"] = (puts["strike"] - price).abs()
        atm_put = puts.sort_values("dist").iloc[0]

        iv = (atm_call["impliedVolatility"] + atm_put["impliedVolatility"]) / 2
        return round(float(iv), 4)
    except Exception as e:
        logger.debug("get_current_iv(%s) failed: %s", ticker, e)
        return 0.30


def get_iv_rank(ticker: str) -> float:
    """
    IV Rank (0–100): (current_iv − 52w_low) / (52w_high − 52w_low) × 100.
    Samples up to 6 expiries; falls back to historical-volatility rank on thin chains.
    Fallback: 50.0.
    """
    try:
        stock    = yf.Ticker(ticker)
        expiries = stock.options
        if not expiries:
            return 50.0

        try:
            price = stock.fast_info.last_price
        except Exception:
            price = None
        if not price:
            return 50.0

        ivs: list[float] = []
        for exp in expiries[:6]:
            try:
                chain  = stock.option_chain(exp)
                calls  = chain.calls.copy()
                calls["dist"] = (calls["strike"] - price).abs()
                atm    = calls.sort_values("dist").iloc[0]
                ivs.append(float(atm["impliedVolatility"]))
            except Exception:
                continue

        if len(ivs) < 2:
            # Fallback: historical-volatility rank
            hist = stock.history(period="1y")["Close"]
            if len(hist) < 20:
                return 50.0
            returns  = np.log(hist / hist.shift(1)).dropna()
            hv_cur   = returns.iloc[-20:].std() * np.sqrt(252)
            hv_high  = returns.rolling(20).std().max() * np.sqrt(252)
            hv_low   = returns.rolling(20).std().min() * np.sqrt(252)
            if hv_high == hv_low:
                return 50.0
            rank = (hv_cur - hv_low) / (hv_high - hv_low) * 100
            return round(float(np.clip(rank, 0, 100)), 1)

        iv_rank = (ivs[0] - min(ivs)) / (max(ivs) - min(ivs)) * 100
        return round(float(np.clip(iv_rank, 0, 100)), 1)

    except Exception as e:
        logger.debug("get_iv_rank(%s) failed: %s", ticker, e)
        return 50.0


def get_vix_level() -> float:
    """Return current VIX level. Fallback: 20.0."""
    try:
        return round(float(yf.Ticker("^VIX").fast_info.last_price), 2)
    except Exception as e:
        logger.debug("get_vix_level failed: %s", e)
        return 20.0


def check_earnings_soon(ticker: str, days: int = 7) -> bool:
    """Return True if earnings are within `days` calendar days. Fallback: False."""
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None or (hasattr(cal, "empty") and cal.empty):
            return False
        for col in ("Earnings Date", "earningsDate"):
            if col in cal.columns:
                date_val = cal[col].iloc[0]
                if hasattr(date_val, "date"):
                    date_val = date_val.date()
                delta = (date_val - datetime.today().date()).days
                return 0 <= delta <= days
        return False
    except Exception as e:
        logger.debug("check_earnings_soon(%s) failed: %s", ticker, e)
        return False


def get_nearest_expiry(ticker: str, target_dte: int = 35) -> str:
    """
    Return the expiry string (YYYY-MM-DD) whose DTE is closest to target_dte.
    Fallback: today + target_dte days.
    """
    try:
        expiries = yf.Ticker(ticker).options
        if not expiries:
            return (datetime.today() + timedelta(days=target_dte)).strftime("%Y-%m-%d")
        today = datetime.today().date()
        best  = min(
            expiries,
            key=lambda e: abs(
                (datetime.strptime(e, "%Y-%m-%d").date() - today).days - target_dte
            ),
        )
        return best
    except Exception as e:
        logger.debug("get_nearest_expiry(%s) failed: %s", ticker, e)
        return (datetime.today() + timedelta(days=target_dte)).strftime("%Y-%m-%d")
