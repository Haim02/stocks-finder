"""
technical_indicators.py — Technical Indicators via FinTA
=========================================================

Uses FinTA (Financial Technical Analysis) library for 80+ indicators.
These are used as features for the XGBoost model training.

Key indicators used:
- RSI (momentum)
- MACD (trend)
- Bollinger Bands (volatility)
- ATR (Average True Range — volatility)
- OBV (On-Balance Volume — accumulation)
- Stochastic (overbought/oversold)
- ADX (trend strength)
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TechnicalSnapshot:
    symbol: str
    price: float

    # Momentum
    rsi_14: float           # 0-100, >70=overbought, <30=oversold
    stoch_k: float          # Stochastic %K
    stoch_d: float          # Stochastic %D

    # Trend
    macd: float             # MACD line
    macd_signal: float      # Signal line
    macd_histogram: float   # MACD - Signal
    adx: float              # ADX trend strength (>25=strong trend)

    # Volatility
    bb_upper: float         # Bollinger Upper Band
    bb_middle: float        # Bollinger Middle (SMA20)
    bb_lower: float         # Bollinger Lower Band
    bb_width: float         # Band width (%)
    atr_14: float           # Average True Range

    # Volume
    obv: float              # On-Balance Volume

    # Signals (derived)
    trend_signal: str       # "bullish" | "bearish" | "neutral"
    momentum_signal: str    # "overbought" | "oversold" | "neutral"
    volatility_signal: str  # "high" | "low" | "normal"
    bb_position: str        # "above_upper" | "below_lower" | "inside"


def get_technical_snapshot(symbol: str, period: str = "3mo") -> Optional[TechnicalSnapshot]:
    """
    Calculate technical indicators for a symbol using FinTA.
    Falls back to manual calculation if FinTA not available.
    """
    try:
        import yfinance as yf
        hist = yf.Ticker(symbol).history(period=period)
        if hist.empty or len(hist) < 30:
            return None

        # FinTA requires specific column names
        df = hist[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]

        price = float(df["close"].iloc[-1])

        try:
            from finta import TA

            rsi = TA.RSI(df, 14)
            rsi_val = float(rsi.iloc[-1]) if not rsi.empty else 50.0

            macd_df = TA.MACD(df)
            if not macd_df.empty and "MACD" in macd_df.columns:
                macd_val = float(macd_df["MACD"].iloc[-1])
                signal_val = float(macd_df["SIGNAL"].iloc[-1])
                histogram = macd_val - signal_val
            else:
                macd_val, signal_val, histogram = 0.0, 0.0, 0.0

            bb = TA.BBANDS(df)
            if not bb.empty:
                bb_upper = float(bb["BB_UPPER"].iloc[-1])
                bb_middle = float(bb["BB_MIDDLE"].iloc[-1])
                bb_lower = float(bb["BB_LOWER"].iloc[-1])
            else:
                bb_upper = price * 1.02
                bb_middle = price
                bb_lower = price * 0.98

            atr = TA.ATR(df, 14)
            atr_val = float(atr.iloc[-1]) if not atr.empty else price * 0.015

            obv = TA.OBV(df)
            obv_val = float(obv.iloc[-1]) if not obv.empty else 0.0

            stoch = TA.STOCH(df)
            if not stoch.empty and "K" in stoch.columns:
                stoch_k = float(stoch["K"].iloc[-1])
                stoch_d = float(stoch["D"].iloc[-1])
            else:
                stoch_k, stoch_d = 50.0, 50.0

            adx = TA.ADX(df)
            adx_val = float(adx.iloc[-1]) if not adx.empty else 20.0

        except ImportError:
            # Manual fallback calculations
            rsi_val = _manual_rsi(df["close"], 14)
            macd_val, signal_val, histogram = _manual_macd(df["close"])
            bb_upper, bb_middle, bb_lower = _manual_bb(df["close"])
            atr_val = float((df["high"] - df["low"]).rolling(14).mean().iloc[-1])
            obv_val = 0.0
            stoch_k, stoch_d = 50.0, 50.0
            adx_val = 20.0

        # Derive signals
        bb_width = round((bb_upper - bb_lower) / bb_middle * 100, 2) if bb_middle > 0 else 0.0

        if price > bb_upper:
            bb_pos = "above_upper"
        elif price < bb_lower:
            bb_pos = "below_lower"
        else:
            bb_pos = "inside"

        # Trend signal
        if macd_val > signal_val and histogram > 0 and adx_val > 20:
            trend = "bullish"
        elif macd_val < signal_val and histogram < 0 and adx_val > 20:
            trend = "bearish"
        else:
            trend = "neutral"

        # Momentum signal
        if rsi_val > 70 or stoch_k > 80:
            momentum = "overbought"
        elif rsi_val < 30 or stoch_k < 20:
            momentum = "oversold"
        else:
            momentum = "neutral"

        # Volatility signal
        if bb_width > 5:
            volatility = "high"
        elif bb_width < 2:
            volatility = "low"
        else:
            volatility = "normal"

        return TechnicalSnapshot(
            symbol=symbol,
            price=round(price, 2),
            rsi_14=round(rsi_val, 1),
            stoch_k=round(stoch_k, 1),
            stoch_d=round(stoch_d, 1),
            macd=round(macd_val, 4),
            macd_signal=round(signal_val, 4),
            macd_histogram=round(histogram, 4),
            adx=round(adx_val, 1),
            bb_upper=round(bb_upper, 2),
            bb_middle=round(bb_middle, 2),
            bb_lower=round(bb_lower, 2),
            bb_width=bb_width,
            atr_14=round(atr_val, 2),
            obv=round(obv_val, 0),
            trend_signal=trend,
            momentum_signal=momentum,
            volatility_signal=volatility,
            bb_position=bb_pos,
        )

    except Exception as e:
        logger.error("Technical indicators failed for %s: %s", symbol, e)
        return None


def _manual_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty else 50.0


def _manual_macd(closes: pd.Series) -> tuple[float, float, float]:
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    hist = macd - signal
    return float(macd.iloc[-1]), float(signal.iloc[-1]), float(hist.iloc[-1])


def _manual_bb(closes: pd.Series, period: int = 20) -> tuple[float, float, float]:
    middle = closes.rolling(period).mean()
    std = closes.rolling(period).std()
    upper = middle + 2 * std
    lower = middle - 2 * std
    return float(upper.iloc[-1]), float(middle.iloc[-1]), float(lower.iloc[-1])


def format_technical_hebrew(snap: TechnicalSnapshot) -> str:
    """Format technical snapshot as Hebrew string for Free Chat."""
    trend_emoji = {"bullish": "🟢 שורי", "bearish": "🔴 דובי", "neutral": "⚪ ניטרלי"}
    momentum_emoji = {"overbought": "⚠️ Overbought", "oversold": "⚠️ Oversold", "neutral": "✅ Normal"}

    rsi_warn = " ⚠️" if snap.rsi_14 > 70 or snap.rsi_14 < 30 else ""
    macd_trend = "↗️" if snap.macd_histogram > 0 else "↘️"

    return (
        f"[ניתוח טכני מורחב — {snap.symbol}]\n"
        f"מחיר: ${snap.price}\n"
        f"RSI(14): {snap.rsi_14}{rsi_warn} | Stoch: {snap.stoch_k:.0f}/{snap.stoch_d:.0f}\n"
        f"MACD: {snap.macd:.3f} {macd_trend} | ADX: {snap.adx:.1f} ({'טרנד חזק' if snap.adx > 25 else 'ללא טרנד'})\n"
        f"BB: ${snap.bb_lower:.2f} — ${snap.bb_upper:.2f} (width: {snap.bb_width:.1f}%)\n"
        f"ATR(14): ${snap.atr_14:.2f}\n"
        f"Trend: {trend_emoji.get(snap.trend_signal, '⚪')} | Momentum: {momentum_emoji.get(snap.momentum_signal, '✅')}\n"
        f"BB Position: {snap.bb_position}"
    )


def get_xgboost_features(symbol: str) -> Optional[dict]:
    """
    Get technical indicator features formatted for XGBoost training.
    Used by train_model.py to enrich training data.
    """
    snap = get_technical_snapshot(symbol)
    if not snap:
        return None
    return {
        "rsi_14": snap.rsi_14,
        "stoch_k": snap.stoch_k,
        "stoch_d": snap.stoch_d,
        "macd": snap.macd,
        "macd_signal": snap.macd_signal,
        "macd_histogram": snap.macd_histogram,
        "adx": snap.adx,
        "bb_width": snap.bb_width,
        "bb_position_encoded": {"above_upper": 2, "inside": 1, "below_lower": 0}.get(snap.bb_position, 1),
        "atr_14": snap.atr_14,
        "trend_encoded": {"bullish": 2, "neutral": 1, "bearish": 0}.get(snap.trend_signal, 1),
        "momentum_encoded": {"overbought": 2, "neutral": 1, "oversold": 0}.get(snap.momentum_signal, 1),
    }
