"""
market_regime_agent.py — Agent 1: Market Regime Analyst
=========================================================

Collects market-wide data every trading day at 10:00 AM Israel time and
produces a structured regime report that Agent 2 (Options Strategist) uses
to decide whether to look for trades.

Data collected:
  - VIX (fear index) via yfinance
  - SPY price + trend (above/below 20-day SMA)
  - SPY IV Rank (estimated from VIX history)
  - Market sentiment average from MongoDB daily_market_sentiment
  - Macro context: Fed rate, CPI YoY, regime (from api_hub)
  - Perplexity Sonar: 4 real-time morning research queries

Output (MarketRegimeReport):
  - verdict: "GREEN" | "YELLOW" | "RED"
  - vix: float
  - spy_trend: "bullish" | "bearish" | "neutral"
  - iv_rank: float (0–100)
  - sentiment_avg: float (1–10)
  - macro_regime: str
  - summary_hebrew: str  ← sent to Telegram
  - raw: dict            ← full data saved to MongoDB
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
import numpy as np

from app.services.perplexity_service import PerplexityService, PerplexityResearch

logger = logging.getLogger(__name__)

_last_macro_snapshot = None  # populated by _fetch_macro(), used in verdict + summary


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class MarketRegimeReport:
    verdict: str          # "GREEN" | "YELLOW" | "RED"
    vix: float
    spy_trend: str        # "bullish" | "bearish" | "neutral"
    iv_rank: float        # 0–100
    sentiment_avg: float  # 1–10, from MongoDB
    macro_regime: str     # from api_hub
    fed_rate: float
    cpi_yoy: float
    summary_hebrew: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    raw: dict = field(default_factory=dict)


# ── Data fetchers ─────────────────────────────────────────────────────────────

def _fetch_vix() -> float:
    """Fetch current VIX level."""
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="2d")
        if hist.empty:
            return 20.0
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as e:
        logger.warning("VIX fetch failed: %s", e)
        return 20.0


def _fetch_spy_trend() -> tuple[str, float, float]:
    """
    Returns (trend, current_price, sma20).
    trend: 'bullish' if price > SMA20, 'bearish' if below, 'neutral' if within 0.5%.
    """
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="30d")
        if len(hist) < 20:
            return "neutral", 0.0, 0.0
        closes = hist["Close"]
        price = float(closes.iloc[-1])
        sma20 = float(closes.tail(20).mean())
        diff_pct = (price - sma20) / sma20 * 100
        if diff_pct > 0.5:
            trend = "bullish"
        elif diff_pct < -0.5:
            trend = "bearish"
        else:
            trend = "neutral"
        return trend, round(price, 2), round(sma20, 2)
    except Exception as e:
        logger.warning("SPY trend fetch failed: %s", e)
        return "neutral", 0.0, 0.0


def _fetch_spy_iv_rank() -> float:
    """
    Estimate SPY IV Rank using VIX history (52-week high/low method).
    IV Rank = (current_VIX - 52w_low) / (52w_high - 52w_low) * 100
    """
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="1y")
        if len(hist) < 50:
            return 50.0
        current = float(hist["Close"].iloc[-1])
        high_52w = float(hist["Close"].max())
        low_52w = float(hist["Close"].min())
        if high_52w == low_52w:
            return 50.0
        iv_rank = (current - low_52w) / (high_52w - low_52w) * 100
        return round(iv_rank, 1)
    except Exception as e:
        logger.warning("IV Rank calc failed: %s", e)
        return 50.0


def _fetch_sentiment_avg() -> float:
    """
    Read today's average sentiment score from MongoDB daily_market_sentiment.
    Returns float 1–10. Returns 5.0 (neutral) if no data.
    """
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        docs = list(db["daily_market_sentiment"].find(
            {"timestamp": {"$gte": today}},
            {"sentiment_score": 1}
        ))
        if not docs:
            # fallback: last 48h
            cutoff = datetime.utcnow() - timedelta(hours=48)
            docs = list(db["daily_market_sentiment"].find(
                {"timestamp": {"$gte": cutoff}},
                {"sentiment_score": 1}
            ))
        if not docs:
            return 5.0
        scores = [d["sentiment_score"] for d in docs if "sentiment_score" in d]
        return round(sum(scores) / len(scores), 2) if scores else 5.0
    except Exception as e:
        logger.warning("Sentiment fetch failed: %s", e)
        return 5.0


def _fetch_macro() -> tuple[str, float, float]:
    """Returns (regime, fed_rate, cpi_yoy) using FRED real data."""
    global _last_macro_snapshot
    try:
        from app.services.fred_service import get_macro_snapshot
        snapshot = get_macro_snapshot()
        _last_macro_snapshot = snapshot
        return snapshot.regime, snapshot.fed_funds_rate, snapshot.cpi_yoy
    except Exception as e:
        logger.warning("FRED macro fetch failed: %s", e)
        return "unknown", 0.0, 0.0


# ── Verdict logic ─────────────────────────────────────────────────────────────

def _detect_perplexity_risks(research: PerplexityResearch) -> tuple[bool, str]:
    """
    Scan Perplexity answers for high-risk keywords.
    Returns (has_major_risk, risk_description).
    """
    if not research.has_data:
        return False, ""

    RED_KEYWORDS = [
        "recession", "crash", "collapse", "crisis", "default",
        "emergency", "panic", "black swan", "war", "systemic",
        "lehman", "bank run", "contagion",
    ]
    YELLOW_KEYWORDS = [
        "concern", "warning", "slowdown", "uncertainty", "tension",
        "hawkish", "rate hike", "inflation surge", "miss", "disappoint",
    ]

    all_text = " ".join(research.raw_responses.values()).lower()

    for kw in RED_KEYWORDS:
        if kw in all_text:
            return True, f"Perplexity זיהה: '{kw}' בחדשות — סיכון גבוה"

    yellow_hits = [kw for kw in YELLOW_KEYWORDS if kw in all_text]
    if len(yellow_hits) >= 2:
        return False, f"Perplexity זיהה: {', '.join(yellow_hits[:3])}"

    return False, ""


def _calculate_verdict(
    vix: float,
    spy_trend: str,
    iv_rank: float,
    sentiment_avg: float,
    macro_regime: str,
    perplexity_major_risk: bool = False,
) -> str:
    """
    RED conditions (any one is enough):
      - VIX > 35 (extreme fear)
      - macro_regime == "recession"
      - VIX > 28 AND spy_trend == "bearish"
      - Perplexity detected major risk keywords

    YELLOW conditions:
      - VIX 22–35
      - sentiment_avg < 4.0
      - spy_trend == "bearish" alone

    GREEN: everything else
    """
    # RED
    if perplexity_major_risk:
        return "RED"
    if vix > 35:
        return "RED"
    if macro_regime and "recession" in macro_regime.lower():
        return "RED"
    if vix > 28 and spy_trend == "bearish":
        return "RED"
    # FRED: inverted yield curve (recession signal)
    if _last_macro_snapshot and _last_macro_snapshot.yield_curve < -0.5:
        return "RED"
    # FRED: high recession probability
    if _last_macro_snapshot and _last_macro_snapshot.recession_probability > 50:
        return "RED"

    # YELLOW
    if vix > 22:
        return "YELLOW"
    if sentiment_avg < 4.0:
        return "YELLOW"
    if spy_trend == "bearish":
        return "YELLOW"

    return "GREEN"


# ── Hebrew summary builder ────────────────────────────────────────────────────

def _build_hebrew_summary(report: MarketRegimeReport) -> str:
    verdict = report.verdict
    vix = report.vix
    spy_trend = report.spy_trend
    iv_rank = report.iv_rank
    sentiment = report.sentiment_avg
    macro = getattr(report, 'macro_snapshot', None) or _last_macro_snapshot
    pcr = getattr(report, 'pcr_signal', None)
    perplexity_notes = getattr(report, 'perplexity_notes', [])

    # Verdict
    verdict_map = {
        "GREEN": ("🟢", "ירוק — מומלץ לפתוח פוזיציות היום"),
        "YELLOW": ("🟡", "צהוב — סחר בזהירות, הקטן סיזינג"),
        "RED": ("🔴", "אדום — לא מומלץ לפתוח פוזיציות חדשות היום"),
    }
    v_emoji, v_text = verdict_map.get(verdict, ("⚪", verdict))

    # VIX interpretation
    if vix < 15:
        vix_note = "נמוך מאוד — שוק רדום, פרמיה זולה"
        vix_impact = "💡 *השפעה:* IV נמוך → אופציות זולות → עדיף לקנות LEAPs, לא למכור פרמיה"
    elif vix < 20:
        vix_note = "✅ תקין — שוק יציב"
        vix_impact = "💡 *השפעה:* סביבה נוחה לכל האסטרטגיות"
    elif vix < 25:
        vix_note = "⚠️ מוגבר — זהירות"
        vix_impact = "💡 *השפעה:* פרמיה מתחילה להיות אטרקטיבית לעסקאות מכירה, הקטן גודל"
    elif vix < 30:
        vix_note = "🔴 גבוה — פחד בשוק"
        vix_impact = "💡 *השפעה:* VIX גבוה = אופציות יקרות = זמן טוב למכור פרמיה, אבל הקטן פוזיציות"
    else:
        vix_note = "🚨 קיצוני — פאניקה"
        vix_impact = "💡 *השפעה:* אל תפתח עסקאות חדשות. VIX מעל 30 = spreads רחבים, fills גרועים"

    # IV Rank interpretation
    if iv_rank >= 50:
        iv_note = "🔥 גבוה — אופציות יקרות"
        iv_impact = "💡 *השפעה:* זמן מצוין למכור פרמיה — Iron Condor, Bull Put Spread"
    elif iv_rank >= 35:
        iv_note = "✅ בינוני-גבוה — סביבה טובה"
        iv_impact = "💡 *השפעה:* Credit Spreads מוגדרי סיכון — מומלץ"
    elif iv_rank >= 20:
        iv_note = "⚠️ בינוני — פרמיה מוגבלת"
        iv_impact = "💡 *השפעה:* Bull Put Spread בזהירות, צמצם יעדי קרדיט"
    else:
        iv_note = "❄️ נמוך — אופציות זולות"
        iv_impact = "💡 *השפעה:* לא זמן למכור פרמיה. שקול LEAPs או Debit Spreads"

    # SPY trend
    spy_note = "📈 עולה" if "bull" in spy_trend.lower() or "עולה" in spy_trend else "📉 יורד" if "bear" in spy_trend.lower() or "יורד" in spy_trend else "➡️ ניטרלי"

    # PCR interpretation
    pcr_section = ""
    if not pcr:
        try:
            from app.services.pcr_signal import get_pcr_signal
            pcr = get_pcr_signal("SPY")
        except Exception:
            pass
    if pcr:
        pcr_val = pcr.pcr if hasattr(pcr, 'pcr') else 0
        put_vol = pcr.put_volume if hasattr(pcr, 'put_volume') else 0
        call_vol = pcr.call_volume if hasattr(pcr, 'call_volume') else 0
        if pcr_val > 1.3:
            pcr_note = f"🟢 {pcr_val:.2f} — שוק פחדני מאוד"
            pcr_impact = "כשכולם קונים Puts מגנים, השוק לרוב **עולה** — סיגנל קונטרריאני חזק"
        elif pcr_val > 1.0:
            pcr_note = f"🟢 {pcr_val:.2f} — שוק פחדני"
            pcr_impact = "יותר מגנים מהמרות — נוטה לעלייה"
        elif pcr_val < 0.7:
            pcr_note = f"🔴 {pcr_val:.2f} — שוק חמדני"
            pcr_impact = "כולם קונים Calls — אופטימיות יתר = סיכון לתיקון"
        else:
            pcr_note = f"⚪ {pcr_val:.2f} — ניטרלי"
            pcr_impact = "אין כיוון ברור מהאופציות"

        pcr_section = (
            f"\n\n📐 *PCR — סנטימנט אופציות:*\n"
            f"• ערך: {pcr_note}\n"
            f"• Puts: `{put_vol:,}` | Calls: `{call_vol:,}`\n"
            f"• 💡 *משמעות:* {pcr_impact}"
        )

    # Macro section
    macro_section = ""
    if macro:
        fed = macro.fed_funds_rate
        curve = macro.yield_curve
        cpi = macro.cpi_yoy
        sp500 = macro.sp500_level
        sp500_chg = macro.sp500_change_1m
        recession_prob = macro.recession_probability
        regime = macro.regime

        curve_note = "✅ תקין — אין סכנת מיתון" if curve > 0 else "⚠️ הפוך — אות מיתון"
        curve_impact = (
            "עקום חיובי = כלכלה בריאה = טוב לשוק"
            if curve > 0
            else "עקום הפוך = היסטורית מנבא מיתון = הזהר!"
        )

        cpi_note = ""
        if cpi > 0:
            cpi_note = f"• אינפלציה (CPI): `{cpi}%`"
            if cpi > 4:
                cpi_note += " 🔴 גבוה — הפד ימשיך להדק"
            elif cpi > 2.5:
                cpi_note += " ⚠️ מעל היעד — הפד זהיר"
            else:
                cpi_note += " ✅ ליד יעד 2%"

        regime_emoji = {
            "expansion": "🟢 התרחבות",
            "recovery": "🔵 התאוששות",
            "slowdown": "🟡 האטה",
            "stagflation": "🟠 סטגפלציה",
            "recession": "🔴 מיתון",
        }.get(regime, regime)

        macro_section = (
            f"\n\n🌍 *נתוני מאקרו (FRED):*\n"
            f"• ריבית Fed: `{fed:.2f}%`\n"
            f"• עקום תשואות (10Y-2Y): `{curve:+.2f}%` — {curve_note}\n"
            f"  💡 {curve_impact}\n"
        )
        if cpi_note:
            macro_section += f"{cpi_note}\n"
        macro_section += (
            f"• S&P 500: `{sp500:,.0f}` ({sp500_chg:+.1f}% החודש)\n"
            f"• הסתברות מיתון: `{recession_prob:.0f}%`\n"
            f"• משטר כלכלי: {regime_emoji}"
        )

    # Perplexity notes
    perp_section = ""
    if perplexity_notes:
        perp_section = "\n\n🔍 *חדשות ואירועים היום:*\n"
        for note in perplexity_notes[:3]:
            clean = str(note).strip()[:120]
            perp_section += f"• {clean}\n"

    # Reason for RED / YELLOW
    reason_section = ""
    if verdict == "RED":
        reason_section = (
            "\n\n⛔ *למה אדום?*\n"
            "הסוכן זיהה סיכון בחדשות או בנתוני מאקרו. "
            "Agent 2 לא יריץ המלצות עסקאות היום. "
            "מחר הסוכן יבדוק שוב."
        )
    elif verdict == "YELLOW":
        reason_section = (
            "\n\n⚠️ *מה לעשות בצהוב?*\n"
            "הקטן סיזינג ל-50%. רק Tier A+ setups. "
            "Agent 2 ירוץ אבל ימליץ על עסקאות שמרניות בלבד."
        )

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    return (
        f"🧠 *Agent 1 — ניתוח שוק יומי*\n"
        f"🕙 {timestamp} שעון ישראל\n"
        f"{'━' * 30}\n\n"
        f"{v_emoji} *ורדיקט: {v_text}*"
        f"{reason_section}\n\n"
        f"{'━' * 30}\n"
        f"📊 *נתוני שוק:*\n"
        f"• VIX: `{vix:.2f}` — {vix_note}\n"
        f"  {vix_impact}\n"
        f"• SPY: {spy_note}\n"
        f"• IV Rank (SPY): `{iv_rank:.1f}%` — {iv_note}\n"
        f"  {iv_impact}\n"
        f"• סנטימנט: `{sentiment:.1f}/10`"
        f"{macro_section}"
        f"{pcr_section}"
        f"{perp_section}"
    )


# ── Main entry point ──────────────────────────────────────────────────────────

class MarketRegimeAgent:
    """
    Agent 1 — Market Regime Analyst.

    Usage:
        agent = MarketRegimeAgent()
        report = agent.run()
        # report.verdict is "GREEN" | "YELLOW" | "RED"
        # report.summary_hebrew is ready to send to Telegram
    """

    def run(self) -> MarketRegimeReport:
        logger.info("=== Agent 1: Market Regime Analyst — START ===")

        # 1. Collect standard market data
        vix = _fetch_vix()
        spy_trend, spy_price, sma20 = _fetch_spy_trend()
        iv_rank = _fetch_spy_iv_rank()
        sentiment_avg = _fetch_sentiment_avg()
        macro_regime, fed_rate, cpi_yoy = _fetch_macro()

        logger.info(
            "Data collected — VIX=%.1f SPY=%s IV_Rank=%.1f Sentiment=%.1f Macro=%s",
            vix, spy_trend, iv_rank, sentiment_avg, macro_regime,
        )

        # 2. Run Perplexity morning research
        perplexity_svc = PerplexityService()
        research = perplexity_svc.run_morning_research()
        perplexity_major_risk, perplexity_risk_desc = _detect_perplexity_risks(research)

        if research.has_data:
            logger.info("Perplexity research complete — major_risk=%s", perplexity_major_risk)
        else:
            logger.info("Perplexity not available — skipping research layer")

        # 3. Calculate verdict
        verdict = _calculate_verdict(
            vix, spy_trend, iv_rank, sentiment_avg, macro_regime,
            perplexity_major_risk=perplexity_major_risk,
        )
        logger.info("Verdict: %s", verdict)

        # 4. Build report
        report = MarketRegimeReport(
            verdict=verdict,
            vix=vix,
            spy_trend=spy_trend,
            iv_rank=iv_rank,
            sentiment_avg=sentiment_avg,
            macro_regime=macro_regime,
            fed_rate=fed_rate,
            cpi_yoy=cpi_yoy,
            summary_hebrew="",
            raw={
                "spy_price": spy_price,
                "sma20": sma20,
                "perplexity": research.raw_responses,
                "perplexity_risk": perplexity_risk_desc,
            },
        )
        report.summary_hebrew = _build_hebrew_summary(report)

        # 5. Save to MongoDB
        self._save_to_mongo(report)

        # 6. Send to Telegram
        self._notify_telegram(report)

        logger.info("=== Agent 1: Market Regime Analyst — DONE ===")
        return report

    def _save_to_mongo(self, report: MarketRegimeReport) -> None:
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            doc = asdict(report)
            db["market_regime_reports"].insert_one(doc)
            logger.info("Regime report saved to MongoDB")
        except Exception as e:
            logger.error("Failed to save regime report to MongoDB: %s", e)

    def _notify_telegram(self, report: MarketRegimeReport) -> None:
        try:
            from app.agent.telegram_bot import notify_trade
            notify_trade(report.summary_hebrew)
            logger.info("Telegram notification sent")
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)


def get_latest_regime() -> Optional[dict]:
    """
    Used by Agent 2 to read the latest regime report from MongoDB.
    Returns the most recent document, or None if not found.
    """
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        doc = db["market_regime_reports"].find_one(
            sort=[("timestamp", -1)]
        )
        if doc:
            doc.pop("_id", None)
        return doc
    except Exception as e:
        logger.error("Failed to read regime report: %s", e)
        return None


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    agent = MarketRegimeAgent()
    report = agent.run()
    print("\n" + report.summary_hebrew)
