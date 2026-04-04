"""
Chart pattern detection helpers.

analyze_chart(ticker, hist) → dict with keys:
  patterns        list[str]   — human-readable pattern names (Hebrew)
  trend_override  str | None  — "bullish" / "bearish" if a strong pattern was found
  summary         str         — one-line Telegram-ready string
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _sma(series: pd.Series, n: int) -> Optional[float]:
    if len(series) < n:
        return None
    return float(series.rolling(n).mean().iloc[-1])


def _local_highs(series: pd.Series, window: int = 5) -> pd.Series:
    return series[(series == series.rolling(window, center=True).max())]


def _local_lows(series: pd.Series, window: int = 5) -> pd.Series:
    return series[(series == series.rolling(window, center=True).min())]


# ── individual pattern checks ─────────────────────────────────────────────────

def _check_ma_crossover(close: pd.Series) -> list[str]:
    """Golden cross (50>200) or Death cross (50<200)."""
    sma50  = _sma(close, 50)
    sma200 = _sma(close, 200)
    if sma50 is None or sma200 is None:
        return []
    if sma50 > sma200 * 1.005:
        return ["חצייה זהובה (MA50 > MA200)"]
    if sma50 < sma200 * 0.995:
        return ["חצייה שחורה (MA50 < MA200)"]
    return []


def _check_price_vs_ma(close: pd.Series) -> list[str]:
    """Price above/below key MAs — simple trend confirmation."""
    price = float(close.iloc[-1])
    patterns = []
    sma20  = _sma(close, 20)
    sma50  = _sma(close, 50)
    sma200 = _sma(close, 200)
    if sma20 and price > sma20 and sma50 and price > sma50:
        patterns.append("מחיר מעל MA20 ו-MA50 (מגמה עולה)")
    elif sma20 and price < sma20 and sma50 and price < sma50:
        patterns.append("מחיר מתחת MA20 ו-MA50 (מגמה יורדת)")
    if sma200:
        if price > sma200 * 1.01:
            patterns.append("מחיר מעל MA200")
        elif price < sma200 * 0.99:
            patterns.append("מחיר מתחת MA200")
    return patterns


def _check_bull_flag(close: pd.Series, vol: Optional[pd.Series] = None) -> list[str]:
    """Bull flag: strong rally (>8% in 10 bars) followed by consolidation (<3%)."""
    if len(close) < 25:
        return []
    pole_end   = close.iloc[-15]
    pole_start = close.iloc[-25]
    flag_high  = close.iloc[-15:-5].max()
    flag_low   = close.iloc[-15:-5].min()
    pole_gain  = (pole_end - pole_start) / max(pole_start, 1e-9)
    flag_range = (flag_high - flag_low) / max(flag_high, 1e-9)
    if pole_gain > 0.08 and flag_range < 0.04:
        return ["דגל שורי (Bull Flag)"]
    return []


def _check_bear_flag(close: pd.Series) -> list[str]:
    """Bear flag: sharp drop followed by tight consolidation."""
    if len(close) < 25:
        return []
    pole_end   = close.iloc[-15]
    pole_start = close.iloc[-25]
    flag_high  = close.iloc[-15:-5].max()
    flag_low   = close.iloc[-15:-5].min()
    pole_drop  = (pole_start - pole_end) / max(pole_start, 1e-9)
    flag_range = (flag_high - flag_low) / max(flag_high, 1e-9)
    if pole_drop > 0.08 and flag_range < 0.04:
        return ["דגל דובי (Bear Flag)"]
    return []


def _check_double_top(high: pd.Series) -> list[str]:
    """Two similar peaks with a trough between them."""
    if len(high) < 30:
        return []
    highs = _local_highs(high, window=5)
    if len(highs) < 2:
        return []
    peaks = highs.iloc[-4:]
    if len(peaks) < 2:
        return []
    p1, p2 = peaks.iloc[-2], peaks.iloc[-1]
    if abs(p1 - p2) / max(p1, 1e-9) < 0.03:
        return ["כפול ראש (Double Top) — איתות דובי"]
    return []


def _check_double_bottom(low: pd.Series) -> list[str]:
    """Two similar troughs with a peak between them."""
    if len(low) < 30:
        return []
    lows = _local_lows(low, window=5)
    if len(lows) < 2:
        return []
    bottoms = lows.iloc[-4:]
    if len(bottoms) < 2:
        return []
    b1, b2 = bottoms.iloc[-2], bottoms.iloc[-1]
    if abs(b1 - b2) / max(b1, 1e-9) < 0.03:
        return ["כפול תחתית (Double Bottom) — איתות שורי"]
    return []


def _check_cup_and_handle(close: pd.Series) -> list[str]:
    """Simplified Cup & Handle: U-shaped recovery + small pullback."""
    if len(close) < 60:
        return []
    segment = close.iloc[-60:]
    cup_left  = float(segment.iloc[:10].mean())
    cup_bottom = float(segment.iloc[20:40].min())
    cup_right  = float(segment.iloc[-15:-5].mean())
    handle     = float(segment.iloc[-5:].min())
    depth = (cup_left - cup_bottom) / max(cup_left, 1e-9)
    recovery = (cup_right - cup_bottom) / max(cup_left - cup_bottom, 1e-9)
    handle_pct = (cup_right - handle) / max(cup_right, 1e-9)
    if 0.15 < depth < 0.40 and recovery > 0.85 and handle_pct < 0.12:
        return ["כוס וידית (Cup & Handle) — איתות שורי חזק"]
    return []


def _check_ascending_triangle(high: pd.Series, low: pd.Series) -> list[str]:
    """Flat resistance + rising lows → ascending triangle (bullish)."""
    if len(high) < 30:
        return []
    recent_highs = high.iloc[-30:]
    recent_lows  = low.iloc[-30:]
    resistance_std = recent_highs.std() / max(recent_highs.mean(), 1e-9)
    low_slope = (float(recent_lows.iloc[-1]) - float(recent_lows.iloc[0])) / max(float(recent_lows.iloc[0]), 1e-9)
    if resistance_std < 0.02 and low_slope > 0.03:
        return ["משולש עולה (Ascending Triangle) — שורי"]
    return []


def _check_descending_triangle(high: pd.Series, low: pd.Series) -> list[str]:
    """Declining highs + flat support → descending triangle (bearish)."""
    if len(high) < 30:
        return []
    recent_highs = high.iloc[-30:]
    recent_lows  = low.iloc[-30:]
    support_std = recent_lows.std() / max(recent_lows.mean(), 1e-9)
    high_slope = (float(recent_highs.iloc[-1]) - float(recent_highs.iloc[0])) / max(float(recent_highs.iloc[0]), 1e-9)
    if support_std < 0.02 and high_slope < -0.03:
        return ["משולש יורד (Descending Triangle) — דובי"]
    return []


def _check_head_and_shoulders(high: pd.Series) -> list[str]:
    """Simplified H&S: three peaks where middle is the tallest."""
    if len(high) < 40:
        return []
    highs = _local_highs(high, window=5)
    if len(highs) < 3:
        return []
    last_three = highs.iloc[-3:]
    left, head, right = last_three.iloc[0], last_three.iloc[1], last_three.iloc[2]
    if head > left * 1.03 and head > right * 1.03 and abs(left - right) / max(left, 1e-9) < 0.05:
        return ["ראש וכתפיים (H&S) — איתות דובי חזק"]
    return []


# ── trend override logic ───────────────────────────────────────────────────────

_BULLISH_PATTERNS = {
    "כפול תחתית (Double Bottom) — איתות שורי",
    "כוס וידית (Cup & Handle) — איתות שורי חזק",
    "משולש עולה (Ascending Triangle) — שורי",
    "דגל שורי (Bull Flag)",
    "חצייה זהובה (MA50 > MA200)",
    "מחיר מעל MA20 ו-MA50 (מגמה עולה)",
}

_BEARISH_PATTERNS = {
    "כפול ראש (Double Top) — איתות דובי",
    "ראש וכתפיים (H&S) — איתות דובי חזק",
    "משולש יורד (Descending Triangle) — דובי",
    "דגל דובי (Bear Flag)",
    "חצייה שחורה (MA50 < MA200)",
    "מחיר מתחת MA20 ו-MA50 (מגמה יורדת)",
}


# ── Bollinger Bands + ADX range-bound detector ───────────────────────────────

def detect_range_bound_for_condor(df: pd.DataFrame) -> dict:
    """
    Use Bollinger Bands (20, 2), ADX (14), and RSI (14) to identify sideways markets
    suitable for Iron Condor strategies.

    Returns dict with:
        is_sideways  : bool
        upper_bb     : float
        lower_bb     : float
        sma          : float
        bandwidth    : float  — (upper - lower) / sma
        adx          : float
        rsi          : float
    """
    result = {
        "is_sideways": False,
        "upper_bb": 0.0, "lower_bb": 0.0, "sma": 0.0,
        "bandwidth": 0.0, "adx": 50.0, "rsi": 50.0,
    }

    if df is None or df.empty or len(df) < 30:
        return result

    try:
        close = df["Close"].dropna()
        high  = df["High"].dropna()  if "High" in df.columns else close
        low   = df["Low"].dropna()   if "Low"  in df.columns else close

        if len(close) < 20:
            return result

        # ── Bollinger Bands (20, 2) ────────────────────────────────────────
        sma  = float(close.rolling(20).mean().iloc[-1])
        std  = float(close.rolling(20).std().iloc[-1])
        upper_bb = sma + 2 * std
        lower_bb = sma - 2 * std
        bandwidth = (upper_bb - lower_bb) / sma if sma > 0 else 1.0

        # ── RSI (14) ───────────────────────────────────────────────────────
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = float((100 - 100 / (1 + rs)).iloc[-1])

        # ── ADX (14) — Wilder method ───────────────────────────────────────
        N = 14
        if len(high) >= N * 2 and len(low) >= N * 2:
            prev_close = close.shift(1)
            tr = pd.concat([
                high - low,
                (high - prev_close).abs(),
                (low  - prev_close).abs(),
            ], axis=1).max(axis=1)

            up_move   = high.diff()
            down_move = (-low.diff())

            plus_dm  = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
            minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

            alpha    = 1.0 / N
            atr      = tr.ewm(alpha=alpha, min_periods=N, adjust=False).mean()
            plus_di  = 100 * plus_dm.ewm(alpha=alpha, min_periods=N, adjust=False).mean() / atr.replace(0, np.nan)
            minus_di = 100 * minus_dm.ewm(alpha=alpha, min_periods=N, adjust=False).mean() / atr.replace(0, np.nan)

            di_sum   = (plus_di + minus_di).replace(0, np.nan)
            dx       = 100 * (plus_di - minus_di).abs() / di_sum
            adx      = float(dx.ewm(alpha=alpha, min_periods=N, adjust=False).mean().iloc[-1])
        else:
            adx = 50.0

        # ── Sideways conditions ────────────────────────────────────────────
        price = float(close.iloc[-1])
        is_sideways = (
            adx < 25                          # weak trend
            and 40 <= rsi <= 60               # neutral momentum
            and lower_bb <= price <= upper_bb # price inside bands
            and bandwidth < 0.15              # narrow bands (squeeze)
        )

        result.update({
            "is_sideways": is_sideways,
            "upper_bb":    round(upper_bb, 2),
            "lower_bb":    round(lower_bb, 2),
            "sma":         round(sma, 2),
            "bandwidth":   round(bandwidth, 4),
            "adx":         round(adx, 1),
            "rsi":         round(rsi, 1),
        })

    except Exception as e:
        logger.debug("detect_range_bound_for_condor failed: %s", e)

    return result


# ── main entry point ──────────────────────────────────────────────────────────

def analyze_chart(ticker: str, hist: pd.DataFrame) -> dict:
    """
    Parameters
    ----------
    ticker : str
    hist   : DataFrame with columns Close, High, Low (daily bars)

    Returns
    -------
    dict with keys:
        patterns       : list[str]
        trend_override : "bullish" | "bearish" | None
        summary        : str   (Telegram-ready, Hebrew)
    """
    result: dict = {
        "patterns": [], "trend_override": None, "summary": "",
        "is_sideways": False, "upper_bb": 0.0, "lower_bb": 0.0,
        "adx": 50.0, "rsi": 50.0,
    }

    if hist is None or hist.empty or "Close" not in hist.columns:
        result["summary"] = "⚠️ אין נתוני גרף"
        return result

    close = hist["Close"].dropna()
    high  = hist["High"].dropna()  if "High"  in hist.columns else close
    low   = hist["Low"].dropna()   if "Low"   in hist.columns else close

    patterns: list[str] = []
    try:
        patterns += _check_ma_crossover(close)
        patterns += _check_price_vs_ma(close)
        patterns += _check_bull_flag(close)
        patterns += _check_bear_flag(close)
        patterns += _check_double_top(high)
        patterns += _check_double_bottom(low)
        patterns += _check_cup_and_handle(close)
        patterns += _check_ascending_triangle(high, low)
        patterns += _check_descending_triangle(high, low)
        patterns += _check_head_and_shoulders(high)
    except Exception:
        logger.warning("chart pattern detection error for %s", ticker, exc_info=True)

    result["patterns"] = patterns

    # Determine trend override
    bull_hits = sum(1 for p in patterns if p in _BULLISH_PATTERNS)
    bear_hits = sum(1 for p in patterns if p in _BEARISH_PATTERNS)
    if bull_hits > bear_hits and bull_hits >= 2:
        result["trend_override"] = "bullish"
    elif bear_hits > bull_hits and bear_hits >= 2:
        result["trend_override"] = "bearish"
    elif bull_hits == 1 and bear_hits == 0:
        result["trend_override"] = "bullish"
    elif bear_hits == 1 and bull_hits == 0:
        result["trend_override"] = "bearish"

    # ── BB/ADX sideways detection ─────────────────────────────────────────
    try:
        bb_data = detect_range_bound_for_condor(hist)
        result.update({
            "is_sideways": bb_data["is_sideways"],
            "upper_bb":    bb_data["upper_bb"],
            "lower_bb":    bb_data["lower_bb"],
            "adx":         bb_data["adx"],
            "rsi":         bb_data["rsi"],
        })
        if bb_data["is_sideways"]:
            # Sideways overrides pattern-based trend
            result["trend_override"] = "neutral"
    except Exception:
        pass

    # ── Summary ───────────────────────────────────────────────────────────
    if result["is_sideways"]:
        adx_val = result["adx"]
        rsi_val = result["rsi"]
        bw_pct  = round(result.get("bandwidth", 0) * 100 if "bandwidth" in result else 0, 1)
        sideways_note = f"📊 *שוק דשדוש* (ADX: {adx_val:.0f}, RSI: {rsi_val:.0f}, BB-Bandwidth: {bw_pct:.1f}%) — מועמד ל-Iron Condor"
        if patterns:
            result["summary"] = sideways_note + " | " + " | ".join(patterns)
        else:
            result["summary"] = sideways_note
    elif patterns:
        result["summary"] = "📐 *תבניות גרף:* " + " | ".join(patterns)
    else:
        result["summary"] = "📐 *תבניות גרף:* לא זוהו תבניות ברורות"

    return result
