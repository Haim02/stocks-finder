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
    Return the most liquid real expiry between 14-45 DTE.
    Among candidates, picks the one with highest total Open Interest.
    Falls back to closest-to-target_dte if no 14-45 DTE expiries exist.
    """
    try:
        stock    = yf.Ticker(ticker)
        expiries = stock.options
        if not expiries:
            return (datetime.today() + timedelta(days=target_dte)).strftime("%Y-%m-%d")

        today = datetime.today().date()

        # Collect all expiries in the 14–45 DTE window
        candidates = []
        for e in expiries:
            exp_date = datetime.strptime(e, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if 14 <= dte <= 45:
                candidates.append((e, dte))

        if not candidates:
            # Fall back: closest to target_dte across all expiries
            return min(
                expiries,
                key=lambda e: abs(
                    (datetime.strptime(e, "%Y-%m-%d").date() - today).days - target_dte
                ),
            )

        if len(candidates) == 1:
            return candidates[0][0]

        # Check total OI on the top 3 nearest-to-30-DTE candidates
        top3 = sorted(candidates, key=lambda x: abs(x[1] - 30))[:3]
        best_expiry = top3[0][0]   # default = closest to 30 DTE
        best_oi     = -1

        for exp, _ in top3:
            try:
                chain    = stock.option_chain(exp)
                total_oi = 0
                if chain.puts is not None and not chain.puts.empty:
                    total_oi += int(chain.puts["openInterest"].fillna(0).sum())
                if chain.calls is not None and not chain.calls.empty:
                    total_oi += int(chain.calls["openInterest"].fillna(0).sum())
                if total_oi > best_oi:
                    best_oi     = total_oi
                    best_expiry = exp
            except Exception:
                continue

        return best_expiry

    except Exception as e:
        logger.debug("get_nearest_expiry(%s) failed: %s", ticker, e)
        return (datetime.today() + timedelta(days=target_dte)).strftime("%Y-%m-%d")


def get_real_option_data(
    ticker: str,
    target_dte: int = 35,
    target_delta: float = 0.30,
    option_type: str = "put",
) -> dict:
    """
    Fetch real option data from yfinance for the strike closest to target_delta.
    Returns dict with: strike, bid, ask, mark, iv, expiry, dte, volume, open_interest.
    Returns empty dict if data unavailable.
    """
    try:
        stock  = yf.Ticker(ticker)
        expiry = get_nearest_expiry(ticker, target_dte)
        chain  = stock.option_chain(expiry)
        today  = datetime.today().date()
        exp_dt = datetime.strptime(expiry, "%Y-%m-%d").date()
        real_dte = (exp_dt - today).days

        df = chain.puts if option_type == "put" else chain.calls
        if df is None or df.empty:
            return {}

        df = df.copy()
        try:
            price = stock.fast_info.last_price
        except Exception:
            price = float(stock.history(period="1d")["Close"].iloc[-1])

        # Target strike based on delta approximation
        if option_type == "put":
            target_strike = price * (1 - target_delta * 0.15)
        else:
            target_strike = price * (1 + target_delta * 0.15)

        df["strike_diff"] = abs(df["strike"] - target_strike)
        best = df.sort_values("strike_diff").iloc[0]

        bid  = float(best.get("bid", 0) or 0)
        ask  = float(best.get("ask", 0) or 0)
        mark = round((bid + ask) / 2, 2) if bid and ask else 0.0
        iv   = float(best.get("impliedVolatility", 0) or 0) * 100  # as percentage

        return {
            "strike":         float(best["strike"]),
            "bid":            bid,
            "ask":            ask,
            "mark":           mark,
            "iv":             round(iv, 1),
            "expiry":         expiry,
            "dte":            real_dte,
            "ticker":         ticker,
            "type":           option_type,
            "volume":         int(best.get("volume", 0) or 0),
            "open_interest":  int(best.get("openInterest", 0) or 0),
        }
    except Exception as e:
        logger.debug("get_real_option_data(%s) failed: %s", ticker, e)
        return {}


def get_real_spread_data(
    ticker: str,
    target_dte: int = 35,
    strategy: str = "bull_put_spread",
) -> dict:
    """
    Fetch real market data for a complete spread strategy.
    Returns actual strikes, real premiums, real DTE from market.
    Returns empty dict on failure.
    """
    try:
        stock  = yf.Ticker(ticker)
        try:
            price = stock.fast_info.last_price
        except Exception:
            price = float(stock.history(period="1d")["Close"].iloc[-1])
        expiry = get_nearest_expiry(ticker, target_dte)
        chain  = stock.option_chain(expiry)
        today  = datetime.today().date()
        exp_dt = datetime.strptime(expiry, "%Y-%m-%d").date()
        real_dte = (exp_dt - today).days

        puts  = chain.puts.copy()  if chain.puts  is not None else None
        calls = chain.calls.copy() if chain.calls is not None else None

        result: dict = {"expiry": expiry, "dte": real_dte, "price": price}

        if strategy == "bull_put_spread" and puts is not None and not puts.empty:
            target_short = price * 0.95
            target_long  = price * 0.90
            puts["diff_short"] = abs(puts["strike"] - target_short)
            puts["diff_long"]  = abs(puts["strike"] - target_long)
            short_row = puts.sort_values("diff_short").iloc[0]
            long_row  = puts.sort_values("diff_long").iloc[0]

            short_bid  = float(short_row.get("bid", 0) or 0)
            short_ask  = float(short_row.get("ask", 0) or 0)
            long_bid   = float(long_row.get("bid", 0) or 0)
            long_ask   = float(long_row.get("ask", 0) or 0)
            short_mark = round((short_bid + short_ask) / 2, 2)
            long_mark  = round((long_bid  + long_ask)  / 2, 2)
            net_credit = round(short_mark - long_mark, 2)
            width      = round(float(short_row["strike"]) - float(long_row["strike"]), 2)
            max_profit = round(net_credit * 100, 2)
            max_loss   = round((width - net_credit) * 100, 2)

            result.update({
                "short_strike": float(short_row["strike"]),
                "long_strike":  float(long_row["strike"]),
                "short_mark":   short_mark,
                "long_mark":    long_mark,
                "net_credit":   net_credit,
                "width":        width,
                "max_profit":   max_profit,
                "max_loss":     max_loss,
                "break_even":   round(float(short_row["strike"]) - net_credit, 2),
                "short_iv":     round(float(short_row.get("impliedVolatility", 0) or 0) * 100, 1),
                "short_volume": int(short_row.get("volume", 0) or 0),
                "rr":           round(max_profit / max_loss, 2) if max_loss > 0 else 0,
            })

        elif strategy == "bear_call_spread" and calls is not None and not calls.empty:
            target_short = price * 1.05
            target_long  = price * 1.10
            calls["diff_short"] = abs(calls["strike"] - target_short)
            calls["diff_long"]  = abs(calls["strike"] - target_long)
            short_row = calls.sort_values("diff_short").iloc[0]
            long_row  = calls.sort_values("diff_long").iloc[0]

            short_mark = round((float(short_row.get("bid", 0) or 0) + float(short_row.get("ask", 0) or 0)) / 2, 2)
            long_mark  = round((float(long_row.get("bid", 0) or 0)  + float(long_row.get("ask", 0) or 0))  / 2, 2)
            net_credit = round(short_mark - long_mark, 2)
            width      = round(float(long_row["strike"]) - float(short_row["strike"]), 2)
            max_profit = round(net_credit * 100, 2)
            max_loss   = round((width - net_credit) * 100, 2)

            result.update({
                "short_strike": float(short_row["strike"]),
                "long_strike":  float(long_row["strike"]),
                "net_credit":   net_credit,
                "width":        width,
                "max_profit":   max_profit,
                "max_loss":     max_loss,
                "break_even":   round(float(short_row["strike"]) + net_credit, 2),
                "rr":           round(max_profit / max_loss, 2) if max_loss > 0 else 0,
            })

        elif strategy == "iron_condor" and puts is not None and calls is not None:
            put_data  = get_real_spread_data(ticker, target_dte, "bull_put_spread")
            call_data = get_real_spread_data(ticker, target_dte, "bear_call_spread")
            if put_data and call_data:
                total_credit = round(
                    put_data.get("net_credit", 0) + call_data.get("net_credit", 0), 2
                )
                result.update({
                    "put_short":  put_data.get("short_strike"),
                    "put_long":   put_data.get("long_strike"),
                    "call_short": call_data.get("short_strike"),
                    "call_long":  call_data.get("long_strike"),
                    "net_credit": total_credit,
                    "max_profit": round(total_credit * 100, 2),
                    "max_loss":   round((put_data.get("width", 5) - total_credit) * 100, 2),
                    "be_low":     round(put_data.get("break_even", 0), 2),
                    "be_high":    round(call_data.get("break_even", 0), 2),
                })

        return result if len(result) > 3 else {}

    except Exception as e:
        logger.debug("get_real_spread_data(%s/%s) failed: %s", ticker, strategy, e)
        return {}
