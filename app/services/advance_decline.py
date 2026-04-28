"""
advance_decline.py — Advance/Decline Line Analysis
====================================================

The A/D Line is the cumulative sum of:
(Advancing stocks - Declining stocks) each day.

KEY SIGNAL — Divergence Detection:
If SPY/QQQ makes a NEW HIGH but A/D Line does NOT → Warning!
Means: only a few large-cap stocks (NVDA, AAPL, MSFT) are driving the index.
Institutional money is concentrated in specific sectors.
The rally is NARROW — not broad-based — potentially unsustainable.

If SPY drops but A/D Line stays HIGH → Bullish divergence.
The broader market is healthy despite index weakness.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_cache: dict = {}
_AD_TTL = 1800  # 30 minutes

SAMPLE_STOCKS = [
    # Tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AMD", "INTC",
    "CRM", "ORCL", "ADBE", "QCOM", "TXN", "AVGO",
    # Finance
    "JPM", "BAC", "GS", "MS", "WFC", "BLK", "AXP", "V", "MA",
    # Healthcare
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK", "ABT",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG",
    # Consumer
    "WMT", "HD", "MCD", "SBUX", "NKE", "TGT", "COST",
    # Industrial
    "CAT", "BA", "GE", "HON", "UPS", "RTX", "LMT",
    # Utilities & REITs
    "NEE", "DUK", "AMT", "PLD",
    # Small/Mid cap
    "IWM", "MDY",
]


@dataclass
class ADLineResult:
    advancing: int
    declining: int
    unchanged: int
    ad_ratio: float
    breadth_score: float

    spy_1m_change: float
    ad_trend: str        # "UP" | "DOWN" | "FLAT"
    divergence: str      # "BULLISH" | "BEARISH" | "CONFIRMED" | "NONE"
    divergence_note: str

    market_breadth: str  # "BROAD" | "NARROW" | "VERY_NARROW"
    breadth_note: str

    interpretation: str
    signal: str          # "🟢" | "🟡" | "🔴"


def get_ad_line() -> Optional[ADLineResult]:
    """
    Calculate Advance/Decline breadth from S&P 500 component sample.
    """
    cached = _cache.get("ad_line")
    if cached:
        data, ts = cached
        if time.time() - ts < _AD_TTL:
            return data

    try:
        import yfinance as yf

        advancing = 0
        declining = 0
        unchanged = 0
        spy_change = 0.0

        try:
            data = yf.download(
                SAMPLE_STOCKS + ["SPY"],
                period="2d",
                progress=False,
                auto_adjust=True,
            )
            closes = data["Close"]

            for ticker in SAMPLE_STOCKS:
                col = closes.get(ticker)
                if col is not None:
                    vals = col.dropna()
                    if len(vals) >= 2:
                        chg = (float(vals.iloc[-1]) / float(vals.iloc[-2]) - 1) * 100
                        if chg > 0.1:
                            advancing += 1
                        elif chg < -0.1:
                            declining += 1
                        else:
                            unchanged += 1

            spy_hist = yf.download("SPY", period="1mo", progress=False, auto_adjust=True)
            if not spy_hist.empty and len(spy_hist) >= 2:
                spy_close = spy_hist["Close"].squeeze()
                spy_change = float((spy_close.iloc[-1] / spy_close.iloc[0] - 1) * 100)

        except Exception as e:
            logger.debug("Batch A/D download failed, falling back: %s", e)
            for ticker in SAMPLE_STOCKS[:25]:
                try:
                    hist = yf.Ticker(ticker).history(period="2d")
                    if len(hist) >= 2:
                        chg = (float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[-2]) - 1) * 100
                        if chg > 0.1:
                            advancing += 1
                        elif chg < -0.1:
                            declining += 1
                        else:
                            unchanged += 1
                except Exception:
                    continue

        total = advancing + declining + unchanged
        if total == 0:
            return None

        ad_ratio = round(advancing / max(declining, 1), 2)
        breadth_score = round(advancing / total * 100, 1)

        if breadth_score >= 70:
            market_breadth = "BROAD"
            breadth_note = (
                f"📈 פריסה רחבה — {advancing}/{total} מניות עולות.\n"
                f"הכסף המוסדי מתפזר על פני כל הסקטורים. עלייה בריאה ובת-קיימא."
            )
        elif breadth_score >= 50:
            market_breadth = "NARROW"
            breadth_note = (
                f"⚠️ פריסה מצומצמת — {advancing}/{total} מניות עולות.\n"
                f"חלק מהסקטורים מפגרים. בדוק אם הטכנולוגיה מובילה לבד."
            )
        else:
            market_breadth = "VERY_NARROW"
            breadth_note = (
                f"🚨 פריסה צרה מאוד — רק {advancing}/{total} מניות עולות!\n"
                f"המדד עולה בגלל מניות ענק בודדות (NVDA/AAPL/MSFT). "
                f"הכסף המוסדי מרוכז — שים לב!"
            )

        ad_trend = "UP" if ad_ratio > 2.0 else ("DOWN" if ad_ratio < 0.5 else "FLAT")

        if spy_change > 3 and breadth_score < 50:
            divergence = "BEARISH"
            divergence_note = (
                f"🚨 *Bearish Divergence מזוהה!*\n"
                f"SPY עלה {spy_change:+.1f}% אבל רק {breadth_score:.0f}% מהמניות עולות.\n"
                f"המדד מובל על ידי מניות ענק בודדות — הכסף המוסדי לא נכנס לרוחב.\n"
                f"זה סימן אזהרה — עלייה לא בת-קיימא."
            )
            signal = "🔴"
        elif spy_change < -3 and breadth_score > 60:
            divergence = "BULLISH"
            divergence_note = (
                f"🟢 *Bullish Divergence מזוהה!*\n"
                f"SPY ירד {spy_change:+.1f}% אבל {breadth_score:.0f}% מהמניות עולות.\n"
                f"הרוחב בריא — הירידה ממוקדת במניות ענק.\n"
                f"השוק הרחב חזק — התיקון עשוי להיות זמני."
            )
            signal = "🟢"
        elif ad_trend == "UP" and spy_change > 0:
            divergence = "CONFIRMED"
            divergence_note = (
                f"✅ *עלייה מאושרת ברוחב השוק!*\n"
                f"SPY עלה {spy_change:+.1f}% ו-{breadth_score:.0f}% מהמניות משתתפות.\n"
                f"עלייה בריאה — הכסף מתפזר על פני כל הסקטורים."
            )
            signal = "🟢"
        else:
            divergence = "NONE"
            divergence_note = f"אין דיברגנס ברור כרגע. A/D Ratio: {ad_ratio:.2f}"
            signal = "🟡"

        result = ADLineResult(
            advancing=advancing,
            declining=declining,
            unchanged=unchanged,
            ad_ratio=ad_ratio,
            breadth_score=breadth_score,
            spy_1m_change=round(spy_change, 1),
            ad_trend=ad_trend,
            divergence=divergence,
            divergence_note=divergence_note,
            market_breadth=market_breadth,
            breadth_note=breadth_note,
            interpretation=(
                f"עולות: {advancing} | יורדות: {declining} | ללא שינוי: {unchanged}\n"
                f"A/D Ratio: {ad_ratio} | Breadth Score: {breadth_score:.0f}%\n"
                f"SPY שינוי חודשי: {spy_change:+.1f}%"
            ),
            signal=signal,
        )

        _cache["ad_line"] = (result, time.time())
        logger.info(
            "A/D Line: advancing=%d declining=%d breadth=%.0f%% divergence=%s",
            advancing, declining, breadth_score, divergence,
        )
        return result

    except Exception as e:
        logger.error("A/D Line calculation failed: %s", e)
        return None


def format_ad_line_hebrew(ad: ADLineResult) -> str:
    """Format A/D Line result for Telegram."""
    breadth_emoji = {
        "BROAD": "🟢",
        "NARROW": "🟡",
        "VERY_NARROW": "🔴",
    }.get(ad.market_breadth, "⚪")

    return (
        f"📈 *Advance/Decline Line Analysis*\n"
        f"{'━'*30}\n\n"

        f"{ad.signal} *דיברגנס: {ad.divergence}*\n"
        f"{ad.divergence_note}\n\n"

        f"{breadth_emoji} *רוחב השוק: {ad.market_breadth}*\n"
        f"{ad.breadth_note}\n\n"

        f"📊 *נתונים:*\n"
        f"• עולות: `{ad.advancing}` | יורדות: `{ad.declining}` | ללא שינוי: `{ad.unchanged}`\n"
        f"• A/D Ratio: `{ad.ad_ratio}` | Breadth Score: `{ad.breadth_score:.0f}%`\n"
        f"• SPY חודש אחרון: `{ad.spy_1m_change:+.1f}%`"
    )
