"""
trade_rules.py — Professional Options Trade Entry/Exit Rules
============================================================
Based on: sujoypaulhome/claude-options-trading-skills (86.7% win rate, production-tested)
Entry rules combine: IV environment + technical setup + market regime.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    should_enter: bool
    strategy: str
    confidence: float
    reasons_for: list[str]
    reasons_against: list[str]
    entry_price: float
    stop_loss: float
    take_profit: float
    size_pct: float


def evaluate_bull_put_entry(
    ticker: str,
    price: float,
    iv_rank: float,
    rsi: float,
    macd_histogram: float,
    adx: float,
    trend: str,
    dte: int,
    vix: float,
    pcr: float = 1.0,
) -> TradeSignal:
    """
    Bull Put Spread entry evaluation.
    All 5 factors must align: IV, RSI, MACD, trend, DTE, VIX.
    """
    reasons_for = []
    reasons_against = []
    score = 0

    if iv_rank >= 50:
        reasons_for.append(f"IV Rank {iv_rank:.0f}% — מצוין למכירת פרמיה")
        score += 30
    elif iv_rank >= 35:
        reasons_for.append(f"IV Rank {iv_rank:.0f}% — טוב למכירת פרמיה")
        score += 20
    elif iv_rank >= 25:
        reasons_for.append(f"IV Rank {iv_rank:.0f}% — מספיק לעסקה שמרנית")
        score += 10
    else:
        reasons_against.append(f"IV Rank {iv_rank:.0f}% — נמוך מדי, פרמיה לא מצדיקה סיכון")
        score -= 20

    if rsi < 40:
        reasons_against.append(f"RSI {rsi:.0f} — oversold, מניה בלחץ")
        score -= 15
    elif rsi < 65:
        reasons_for.append(f"RSI {rsi:.0f} — תקין, לא overbought")
        score += 10
    elif rsi < 75:
        reasons_for.append(f"RSI {rsi:.0f} — ניטרלי")
        score += 5
    else:
        reasons_against.append(f"RSI {rsi:.0f} — overbought, זהירות")
        score -= 10

    if macd_histogram > 0:
        reasons_for.append("MACD חיובי — מומנטום שורי")
        score += 10
    else:
        reasons_against.append("MACD שלילי — מומנטום דובי")
        score -= 5

    if trend == "bullish":
        reasons_for.append("טרנד שורי — מתאים ל-Bull Put")
        score += 15
    elif trend == "neutral":
        reasons_for.append("טרנד ניטרלי — בסדר ל-Bull Put")
        score += 5
    else:
        reasons_against.append("טרנד דובי — לא מתאים ל-Bull Put")
        score -= 20

    if 30 <= dte <= 45:
        reasons_for.append(f"DTE {dte} — sweet spot מושלם")
        score += 10
    elif 20 <= dte < 30:
        reasons_for.append(f"DTE {dte} — קצת קצר אבל סביר")
        score += 5
    else:
        reasons_against.append(f"DTE {dte} — לא בטווח המומלץ 30-45")
        score -= 10

    if vix < 18:
        reasons_for.append(f"VIX {vix:.1f} — שוק רגוע")
        score += 5
    elif vix < 25:
        score += 0
    elif vix < 30:
        reasons_against.append(f"VIX {vix:.1f} — מוגבר, הקטן גודל")
        score -= 10
    else:
        reasons_against.append(f"VIX {vix:.1f} — גבוה מדי למכירת פרמיה")
        score -= 25

    if pcr > 1.2:
        reasons_for.append(f"PCR {pcr:.2f} — שוק פחדני = קונטרריאני bullish")
        score += 10
    elif pcr < 0.7:
        reasons_against.append(f"PCR {pcr:.2f} — שוק חמדני מדי")
        score -= 5

    confidence = max(0.0, min(100.0, 50.0 + score))
    should_enter = confidence >= 60

    if vix > 25:
        size_pct = 1.5
    elif confidence >= 80:
        size_pct = 4.0
    elif confidence >= 70:
        size_pct = 3.0
    else:
        size_pct = 2.0

    return TradeSignal(
        should_enter=should_enter,
        strategy="Bull Put Spread",
        confidence=confidence,
        reasons_for=reasons_for,
        reasons_against=reasons_against,
        entry_price=price,
        stop_loss=price * 0.95,
        take_profit=price * 1.05,
        size_pct=size_pct,
    )


def evaluate_iron_condor_entry(
    ticker: str,
    price: float,
    iv_rank: float,
    rsi: float,
    adx: float,
    bb_width: float,
    vix: float,
    has_earnings_soon: bool,
) -> TradeSignal:
    """
    Iron Condor entry evaluation.
    Needs: high IV + LOW directional movement + no upcoming earnings.
    ADX < 20 is mandatory — a trending market kills both sides.
    """
    reasons_for = []
    reasons_against = []
    score = 0

    if iv_rank >= 50:
        reasons_for.append(f"IV Rank {iv_rank:.0f}% — מצוין לIron Condor")
        score += 30
    elif iv_rank >= 35:
        reasons_for.append(f"IV Rank {iv_rank:.0f}% — מספיק")
        score += 15
    else:
        reasons_against.append(f"IV Rank {iv_rank:.0f}% — נמוך מדי, שני הצדדים לא מספיקים")
        score -= 30

    if adx < 20:
        reasons_for.append(f"ADX {adx:.0f} — אין טרנד = מושלם לCondor")
        score += 25
    elif adx < 25:
        reasons_for.append(f"ADX {adx:.0f} — טרנד חלש = בסדר")
        score += 10
    else:
        reasons_against.append(f"ADX {adx:.0f} — טרנד חזק = Iron Condor מסוכן")
        score -= 25

    if bb_width < 3:
        reasons_for.append("Bollinger Bands צרות — מניה בטווח")
        score += 15
    elif bb_width > 6:
        reasons_against.append("Bollinger Bands רחבות — מניה נדיפה מדי")
        score -= 15

    if 40 <= rsi <= 60:
        reasons_for.append(f"RSI {rsi:.0f} — ניטרלי מושלם לCondor")
        score += 10
    else:
        reasons_against.append(f"RSI {rsi:.0f} — לא ניטרלי מספיק")
        score -= 10

    if has_earnings_soon:
        reasons_against.append("⚠️ יש Earnings קרובים — אל תיכנס לIron Condor!")
        score -= 50
    else:
        reasons_for.append("אין Earnings קרובים ✅")
        score += 10

    if vix > 30:
        reasons_against.append(f"VIX {vix:.1f} — גבוה מדי לCondor")
        score -= 20

    confidence = max(0.0, min(100.0, 50.0 + score))
    should_enter = confidence >= 65
    size_pct = 3.0 if confidence >= 75 else 2.0

    return TradeSignal(
        should_enter=should_enter,
        strategy="Iron Condor",
        confidence=confidence,
        reasons_for=reasons_for,
        reasons_against=reasons_against,
        entry_price=price,
        stop_loss=0.0,
        take_profit=0.0,
        size_pct=size_pct,
    )


def format_signal_hebrew(signal: TradeSignal, ticker: str) -> str:
    """Format TradeSignal as Hebrew Telegram message."""
    decision = "✅ כן — היכנס לעסקה" if signal.should_enter else "❌ לא — דלג על עסקה זו"
    conf_emoji = "🟢" if signal.confidence >= 75 else ("🟡" if signal.confidence >= 60 else "🔴")

    reasons_for_text = "\n".join(f"  ✅ {r}" for r in signal.reasons_for) or "  אין"
    reasons_against_text = "\n".join(f"  ⚠️ {r}" for r in signal.reasons_against) or "  אין"

    return (
        f"📊 *הערכת עסקה — {ticker} {signal.strategy}*\n"
        f"{'━' * 30}\n\n"
        f"{conf_emoji} *ביטחון: {signal.confidence:.0f}%*\n"
        f"🎯 *החלטה: {decision}*\n\n"
        f"👍 *סיבות לכניסה:*\n{reasons_for_text}\n\n"
        f"👎 *סיבות נגד:*\n{reasons_against_text}\n\n"
        f"📐 *גודל מומלץ: {signal.size_pct:.1f}% מהחשבון*"
    )
