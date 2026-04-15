"""
pcr_signal.py — Put/Call Ratio (PCR) Market Sentiment Signal
=============================================================

PCR = Total Put Volume / Total Call Volume

Interpretation:
- PCR > 1.2  → Market is FEARFUL → Contrarian bullish signal
- PCR > 1.5  → Extreme fear → Strong bullish signal (market oversold)
- PCR 0.8-1.2 → Neutral
- PCR < 0.8  → Market is GREEDY → Contrarian bearish signal
- PCR < 0.6  → Extreme greed → Strong bearish signal (market overbought)

Source: yfinance options volume data on SPY (most liquid)
Used by: Agent 1 (Market Regime) as additional confirmation signal
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_PCR_TTL = 1800  # 30 minutes
_pcr_cache: dict[str, tuple] = {}  # symbol → (PCRSignal, timestamp)


@dataclass
class PCRSignal:
    pcr: float              # Put/Call Ratio value
    put_volume: int
    call_volume: int
    signal: str             # "bullish" | "bearish" | "neutral"
    strength: str           # "strong" | "moderate" | "weak"
    interpretation: str     # Hebrew explanation
    regime_impact: str      # "GREEN_boost" | "RED_boost" | "neutral"


def get_pcr_signal(symbol: str = "SPY") -> Optional[PCRSignal]:
    """
    Calculate Put/Call Ratio from today's options volume.
    Uses the nearest expiration for most accurate sentiment reading.
    Results cached for 30 minutes.
    """
    cached = _pcr_cache.get(symbol)
    if cached and (time.time() - cached[1]) < _PCR_TTL:
        logger.debug("PCR cache hit for %s", symbol)
        return cached[0]

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return None

        # Use nearest expiration for most sensitive sentiment
        exp = expirations[0]
        chain = ticker.option_chain(exp)

        calls = chain.calls
        puts = chain.puts

        if calls.empty or puts.empty:
            return None

        # Sum total volume
        total_call_vol = int(calls["volume"].fillna(0).sum())
        total_put_vol = int(puts["volume"].fillna(0).sum())

        if total_call_vol == 0:
            return None

        pcr = round(total_put_vol / total_call_vol, 3)

        # Interpret
        if pcr > 1.5:
            signal = "bullish"
            strength = "strong"
            interpretation = f"PCR={pcr:.2f} — פחד קיצוני בשוק. סיגנל קונטרריאני BULLISH חזק. שוק מוכר יתר."
            regime_impact = "GREEN_boost"
        elif pcr > 1.2:
            signal = "bullish"
            strength = "moderate"
            interpretation = f"PCR={pcr:.2f} — שוק פחדי. נוטה לעלייה. מוכרי ה-Put חושבים שהשוק ירד — זה לרוב קונטרריאני."
            regime_impact = "GREEN_boost"
        elif pcr < 0.6:
            signal = "bearish"
            strength = "strong"
            interpretation = f"PCR={pcr:.2f} — חמדנות קיצונית. כולם קונים Calls. סיגנל קונטרריאני BEARISH חזק."
            regime_impact = "RED_boost"
        elif pcr < 0.8:
            signal = "bearish"
            strength = "moderate"
            interpretation = f"PCR={pcr:.2f} — שוק אופטימי מדי. זהירות מפני ירידה."
            regime_impact = "RED_boost"
        else:
            signal = "neutral"
            strength = "weak"
            interpretation = f"PCR={pcr:.2f} — סנטימנט ניטרלי. אין אות חזק."
            regime_impact = "neutral"

        logger.info("PCR %s: %.3f → %s (%s)", symbol, pcr, signal, strength)

        result = PCRSignal(
            pcr=pcr,
            put_volume=total_put_vol,
            call_volume=total_call_vol,
            signal=signal,
            strength=strength,
            interpretation=interpretation,
            regime_impact=regime_impact,
        )
        _pcr_cache[symbol] = (result, time.time())
        return result

    except Exception as e:
        logger.warning("PCR calculation failed for %s: %s", symbol, e)
        return None


def format_pcr_hebrew(pcr: PCRSignal) -> str:
    signal_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(pcr.signal, "⚪")
    return (
        f"[PCR Signal — סנטימנט אופציות]\n"
        f"{signal_emoji} PCR: {pcr.pcr:.3f} | "
        f"Puts: {pcr.put_volume:,} | Calls: {pcr.call_volume:,}\n"
        f"{pcr.interpretation}"
    )
