"""
News Impact Analyzer — cross-references MongoDB training_events
to predict whether news is positive/negative/neutral for a ticker.

Learns from past: "when NVDA had earnings news → price went up 68% of the time"
Uses training_events collection which stores past scan outcomes.
"""

import logging

logger = logging.getLogger(__name__)

BULLISH_KEYWORDS = [
    "earnings beat", "record revenue", "guidance raised", "buyback",
    "dividend increase", "fda approval", "contract win", "acquisition",
    "upgrade", "price target raised", "partnership", "expansion",
    "record high", "profit", "beat expectations", "strong demand",
]

BEARISH_KEYWORDS = [
    "earnings miss", "guidance cut", "layoffs", "recall", "lawsuit",
    "investigation", "downgrade", "price target cut", "loss", "decline",
    "warning", "shortage", "delay", "competition", "tariff", "fine",
    "bankruptcy", "fraud", "resignation", "scandal",
]

MACRO_KEYWORDS = {
    "fed rate hike":  {"direction": "bearish",  "sectors": ["tech", "growth"]},
    "fed rate cut":   {"direction": "bullish",  "sectors": ["all"]},
    "inflation":      {"direction": "mixed",    "sectors": ["consumer"]},
    "recession":      {"direction": "bearish",  "sectors": ["all"]},
    "tariff":         {"direction": "bearish",  "sectors": ["manufacturing", "retail"]},
    "strong jobs":    {"direction": "bullish",  "sectors": ["consumer", "retail"]},
    "oil price":      {"direction": "mixed",    "sectors": ["energy"]},
    "china tension":  {"direction": "bearish",  "sectors": ["tech", "semiconductor"]},
    "ai boom":        {"direction": "bullish",  "sectors": ["tech", "semiconductor"]},
}


def analyze_news_impact(
    ticker: str,
    headlines: list[str],
    sector: str = "",
    price: float = 0.0,
) -> dict:
    """
    Analyze news headlines and cross-reference with MongoDB training history
    to predict likely price impact.

    Returns:
        sentiment_score      : float  — -1.0 to +1.0
        sentiment_label      : str    — Hebrew label with emoji
        bullish_signals      : list[str]
        bearish_signals      : list[str]
        macro_impact         : str
        historical_win_rate  : float | None
        historical_note      : str
        recommended_strategy : str
        confidence           : str    — גבוה / בינוני / נמוך
    """
    if not headlines:
        return _neutral_result("אין חדשות")

    combined = " ".join(headlines).lower()
    bull_hits, bear_hits = [], []

    for kw in BULLISH_KEYWORDS:
        if kw in combined:
            bull_hits.append(kw)

    for kw in BEARISH_KEYWORDS:
        if kw in combined:
            bear_hits.append(kw)

    # Macro impact
    macro_notes = []
    for macro_kw, impact in MACRO_KEYWORDS.items():
        if macro_kw in combined:
            relevant = (
                impact["sectors"] == ["all"]
                or sector.lower() in [s.lower() for s in impact["sectors"]]
            )
            if relevant:
                macro_notes.append(
                    f"{macro_kw} → השפעה {impact['direction']} על {sector or 'המניה'}"
                )

    # MongoDB historical cross-reference
    historical_win_rate = None
    historical_note     = ""
    try:
        from app.data.mongo_client import MongoDB
        db   = MongoDB.get_db()
        past = list(db["training_events"].find({
            "ticker":  ticker.upper(),
            "labeled": True,
            "label":   {"$ne": None},
        }).sort("scan_at", -1).limit(20))

        if past:
            wins  = sum(1 for e in past if e.get("label") is True)
            total = len(past)
            historical_win_rate = round(wins / total * 100, 1)
            historical_note = (
                f"היסטוריה: {historical_win_rate}% ניצחון ב-{total} עסקאות קודמות"
            )
            strat_wins: dict[str, int] = {}
            for e in [x for x in past if x.get("label") is True]:
                s = e.get("strategy_name") or e.get("strategy") or "unknown"
                strat_wins[s] = strat_wins.get(s, 0) + 1
            if strat_wins:
                best = max(strat_wins, key=strat_wins.get)
                historical_note += f" | אסטרטגיה מנצחת: {best}"
    except Exception:
        pass

    # Net sentiment
    total_kw = len(bull_hits) + len(bear_hits)
    sentiment_score = (len(bull_hits) - len(bear_hits)) / total_kw if total_kw > 0 else 0.0

    if historical_win_rate is not None:
        hist_boost = (historical_win_rate - 50) / 200
        sentiment_score = max(-1.0, min(1.0, sentiment_score + hist_boost))

    if sentiment_score > 0.3:
        label        = "שורי 🟢"
        confidence   = "גבוה" if sentiment_score > 0.6 else "בינוני"
        rec_strategy = "Bull Put Spread / Cash-Secured Put"
    elif sentiment_score < -0.3:
        label        = "דובי 🔴"
        confidence   = "גבוה" if sentiment_score < -0.6 else "בינוני"
        rec_strategy = "Bear Call Spread / Bear Put Spread"
    else:
        label        = "ניטרלי 🟡"
        confidence   = "נמוך"
        rec_strategy = "Iron Condor / Calendar Spread"

    return {
        "sentiment_score":      round(sentiment_score, 2),
        "sentiment_label":      label,
        "bullish_signals":      bull_hits[:3],
        "bearish_signals":      bear_hits[:3],
        "macro_impact":         " | ".join(macro_notes[:2]) if macro_notes else "אין השפעה מאקרו מזוהה",
        "historical_win_rate":  historical_win_rate,
        "historical_note":      historical_note,
        "recommended_strategy": rec_strategy,
        "confidence":           confidence,
    }


def _neutral_result(reason: str) -> dict:
    return {
        "sentiment_score":      0.0,
        "sentiment_label":      "ניטרלי 🟡",
        "bullish_signals":      [],
        "bearish_signals":      [],
        "macro_impact":         reason,
        "historical_win_rate":  None,
        "historical_note":      "",
        "recommended_strategy": "Iron Condor",
        "confidence":           "נמוך",
    }


# ── New unified entry point using finvizfinance ───────────────────────────────

_BULL_WORDS = [
    "beat", "upgrade", "growth", "raised", "record", "approval", "buyback",
    "dividend", "partnership", "expansion", "wins", "profit", "strong",
]
_BEAR_WORDS = [
    "miss", "downgrade", "cut", "loss", "investigation", "recall", "lawsuit",
    "fine", "delay", "warning", "decline", "layoff", "fraud", "shortage",
]


def analyze_ticker_context(ticker: str, price: float = 0.0) -> dict:
    """
    Unified context analysis using finvizfinance (real news + fundamentals)
    cross-referenced with MongoDB training_events for historical win rate.

    Returns:
        sentiment        : "bullish" | "bearish" | "neutral"
        sentiment_score  : float  — -1.0 to +1.0
        historical_win_rate : float | None
        best_hist_strategy  : str | None
        news_summary     : list[str]
        sector           : str
        note             : str  — Hebrew summary line
    """
    context: dict = {
        "sentiment":            "neutral",
        "sentiment_score":      0.0,
        "historical_win_rate":  None,
        "best_hist_strategy":   None,
        "news_summary":         [],
        "sector":               "Unknown",
        "note":                 "",
    }

    # ── finvizfinance: sector + news ──────────────────────────────────────
    try:
        from finvizfinance.quote import finvizfinance as fvf
        stock = fvf(ticker)

        try:
            fund = stock.ticker_fundament()
            context["sector"] = fund.get("Sector", "Unknown")
        except Exception:
            pass

        try:
            news_df = stock.ticker_news()
            if news_df is not None and not news_df.empty:
                headlines = [
                    str(row.get("Title", "")).replace("\r\n", " ").strip()
                    for _, row in news_df.head(5).iterrows()
                ]
                context["news_summary"] = [h for h in headlines if h]
                text       = " ".join(context["news_summary"]).lower()
                bull_score = sum(1 for w in _BULL_WORDS if w in text)
                bear_score = sum(1 for w in _BEAR_WORDS if w in text)
                if bull_score + bear_score > 0:
                    context["sentiment_score"] = (bull_score - bear_score) / (bull_score + bear_score)
        except Exception:
            pass

    except Exception as e:
        logger.debug("finvizfinance context failed for %s: %s", ticker, e)

    # ── MongoDB historical cross-reference ────────────────────────────────
    try:
        from app.data.mongo_client import MongoDB
        db   = MongoDB.get_db()
        past = list(db["training_events"].find({
            "ticker":  ticker.upper(),
            "labeled": True,
            "label":   {"$ne": None},
        }).sort("scan_at", -1).limit(30))

        if not past:
            # legacy collection name
            past = list(db["train"].find({
                "ticker":    ticker.upper(),
                "processed": True,
                "label":     {"$ne": None},
            }).sort("timestamp", -1).limit(30))

        if past:
            wins     = sum(1 for e in past if e.get("label") in (True, 1))
            total    = len(past)
            win_rate = round(wins / total * 100, 1)
            context["historical_win_rate"] = win_rate

            strat_wins: dict[str, int] = {}
            for e in past:
                if e.get("label") in (True, 1):
                    s = e.get("strategy_name") or e.get("strategy") or "unknown"
                    strat_wins[s] = strat_wins.get(s, 0) + 1
            if strat_wins:
                context["best_hist_strategy"] = max(strat_wins, key=strat_wins.get)

            note = f"היסטוריה: {win_rate}% ניצחון ב-{total} עסקאות"
            if context["best_hist_strategy"]:
                note += f" | אסטרטגיה מנצחת: {context['best_hist_strategy']}"
            if win_rate < 35:
                note += " | ⚠️ Win rate נמוך — זהירות"
                context["sentiment"] = "bearish"
            context["note"] = note

    except Exception as e:
        logger.debug("MongoDB cross-reference failed for %s: %s", ticker, e)

    # ── Final sentiment label ─────────────────────────────────────────────
    score = context["sentiment_score"]
    if context["sentiment"] != "bearish":   # don't override DB-forced bearish
        if score > 0.3:
            context["sentiment"] = "bullish"
        elif score < -0.3:
            context["sentiment"] = "bearish"
        else:
            context["sentiment"] = "neutral"

    return context
