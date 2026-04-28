"""
news_alert_engine.py — Real-Time News Alert System
====================================================

Runs automatically every 15 min during US market hours (16:00–23:00 Israel).
Scans watchlist for breaking catalysts via Perplexity → sends Telegram alerts.

Catalyst types and expected moves:
  pentagon / defense contract → 8–15%
  FDA approval / rejection → 15–40%
  acquisition / merger → 15–30%
  earnings beat / miss → 5–15%
  analyst upgrade / downgrade → 3–8%
  short squeeze → 10–25%
  insider buying → 3–7%
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 65  # minimum catalyst score to send alert

CATALYST_KEYWORDS: dict[str, int] = {
    # High-impact (score 80–95)
    "fda approval": 90,
    "fda approved": 90,
    "fda rejection": 88,
    "fda rejected": 88,
    "acquisition": 85,
    "acquired by": 85,
    "merger": 82,
    "takeover": 85,
    "buyout": 83,
    "going private": 80,
    "pentagon contract": 90,
    "defense contract": 88,
    "government contract": 82,
    "dod contract": 88,
    "short squeeze": 80,
    "gamma squeeze": 80,
    "short interest": 72,
    # Medium-high (score 65–79)
    "earnings beat": 75,
    "beat estimates": 72,
    "beat expectations": 72,
    "earnings miss": 73,
    "missed estimates": 70,
    "guidance raised": 70,
    "guidance cut": 70,
    "raised guidance": 70,
    "lowered guidance": 70,
    "analyst upgrade": 68,
    "upgraded to buy": 70,
    "upgraded to strong buy": 75,
    "analyst downgrade": 68,
    "downgraded to sell": 70,
    "price target raised": 66,
    "price target cut": 66,
    "insider buying": 68,
    "insider purchase": 66,
    "ceo bought": 67,
    "stock buyback": 65,
    "share repurchase": 65,
    # Medium (score 55–65)
    "partnership": 60,
    "collaboration": 58,
    "joint venture": 62,
    "product launch": 60,
    "new product": 58,
    "revenue guidance": 62,
    "clinical trial": 65,
    "phase 3": 68,
    "phase 2": 62,
    "data breach": 65,
    "sec investigation": 70,
    "doj investigation": 70,
    "class action": 65,
    "recall": 62,
}

DEFAULT_WATCHLIST = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA",
    "AMD", "PLTR", "COIN", "LLY", "AXON", "RKLB", "MSTR", "HOOD",
    "SOFI", "IONQ",
]

_WATCHLIST_KEY = "news_watchlist"
_dedup_cache: dict[str, float] = {}  # "TICKER|headline" → timestamp
_DEDUP_TTL = 21600  # 6 hours


# ══════════════════════════════════════════════════════════════════════════════
# Data model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NewsAlert:
    ticker: str
    headline: str
    catalyst_type: str
    catalyst_score: int
    expected_move: str
    magnitude: str           # "HIGH" | "MEDIUM" | "LOW"
    action_recommendation: str
    iv_rank: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "Perplexity/Sonar"
    raw_text: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Watchlist — MongoDB user_settings
# ══════════════════════════════════════════════════════════════════════════════

def _get_watchlist() -> list[str]:
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        doc = db["user_settings"].find_one({"key": _WATCHLIST_KEY})
        if doc and "tickers" in doc:
            return [t.upper() for t in doc["tickers"]]
    except Exception as e:
        logger.debug("Failed to load watchlist from MongoDB: %s", e)
    return list(DEFAULT_WATCHLIST)


def _save_watchlist(tickers: list[str]) -> None:
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        db["user_settings"].update_one(
            {"key": _WATCHLIST_KEY},
            {"$set": {"key": _WATCHLIST_KEY, "tickers": [t.upper() for t in tickers]}},
            upsert=True,
        )
    except Exception as e:
        logger.error("Failed to save watchlist: %s", e)


def add_to_watchlist(ticker: str) -> list[str]:
    wl = _get_watchlist()
    ticker = ticker.upper()
    if ticker not in wl:
        wl.append(ticker)
        _save_watchlist(wl)
    return wl


def remove_from_watchlist(ticker: str) -> list[str]:
    wl = _get_watchlist()
    ticker = ticker.upper()
    wl = [t for t in wl if t != ticker]
    _save_watchlist(wl)
    return wl


def reset_watchlist() -> list[str]:
    _save_watchlist(list(DEFAULT_WATCHLIST))
    return list(DEFAULT_WATCHLIST)


# ══════════════════════════════════════════════════════════════════════════════
# Catalyst detection
# ══════════════════════════════════════════════════════════════════════════════

def _detect_catalyst_type(text: str) -> tuple[str, int]:
    """Returns (catalyst_type, score). Higher score = stronger catalyst."""
    text_lower = text.lower()
    best_type = "general"
    best_score = 0

    for keyword, score in CATALYST_KEYWORDS.items():
        if keyword in text_lower and score > best_score:
            best_score = score
            best_type = keyword

    return best_type, best_score


def _estimate_move(catalyst_type: str, score: int) -> tuple[str, str]:
    """Returns (expected_move_str, magnitude)."""
    if score >= 85:
        return "15–40%", "HIGH"
    elif score >= 75:
        return "8–15%", "HIGH"
    elif score >= 68:
        return "5–10%", "MEDIUM"
    elif score >= 60:
        return "3–7%", "MEDIUM"
    else:
        return "2–5%", "LOW"


def _recommend_action(catalyst_type: str, score: int, iv_rank: float) -> str:
    """Hebrew action recommendation based on catalyst + IV."""
    cat = catalyst_type.lower()

    # Bullish catalysts
    if any(k in cat for k in ["approval", "beat", "upgrade", "contract", "buyout",
                               "acquisition", "raised guidance", "insider buy", "buyback"]):
        if iv_rank >= 35:
            return "שקול Bull Put Spread — IV גבוה, מכור פרמיה"
        else:
            return "שקול Long Call / Bull Call Spread — כיוון ברור"

    # Bearish catalysts
    if any(k in cat for k in ["rejection", "miss", "downgrade", "lowered guidance",
                               "investigation", "recall", "class action", "breach"]):
        if iv_rank >= 35:
            return "שקול Bear Call Spread — IV גבוה, מכור פרמיה בצד מעלה"
        else:
            return "שקול Long Put / Bear Put Spread — לחץ מטה צפוי"

    # Binary event
    if any(k in cat for k in ["fda", "clinical", "phase", "squeeze", "merger"]):
        if iv_rank >= 50:
            return "זהירות — IV קפץ, מכירת פרמיה מסוכנת לפני בינארי"
        else:
            return "שקול Long Straddle — מהלך חד צפוי לשני הכיוונים"

    # Default
    return "עקוב אחרי המחיר — אמת ב-TradingView לפני כניסה"


# ══════════════════════════════════════════════════════════════════════════════
# Dedup
# ══════════════════════════════════════════════════════════════════════════════

def _is_duplicate(ticker: str, headline: str) -> bool:
    key = f"{ticker}|{headline[:60]}"
    ts = _dedup_cache.get(key)
    if ts and time.time() - ts < _DEDUP_TTL:
        return True
    _dedup_cache[key] = time.time()
    # Cleanup old entries
    now = time.time()
    expired = [k for k, v in _dedup_cache.items() if now - v > _DEDUP_TTL]
    for k in expired:
        del _dedup_cache[k]
    return False


# ══════════════════════════════════════════════════════════════════════════════
# Telegram alert sender
# ══════════════════════════════════════════════════════════════════════════════

async def _send_telegram_alert(alert: NewsAlert) -> None:
    from app.core.config import settings

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.warning("Telegram credentials missing — alert not sent for %s", alert.ticker)
        return

    magnitude_emoji = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(alert.magnitude, "📰")
    score_bar = "🔥" * min(5, alert.catalyst_score // 20)

    text = (
        f"{magnitude_emoji} *NEWS ALERT — {alert.ticker}*\n"
        f"{'━'*28}\n\n"
        f"📰 *{alert.headline[:120]}*\n\n"
        f"🎯 *Catalyst:* `{alert.catalyst_type}`\n"
        f"💥 *Score:* `{alert.catalyst_score}/100` {score_bar}\n"
        f"📊 *צפי תנועה:* `{alert.expected_move}`\n"
        f"📈 *IV Rank:* `{alert.iv_rank:.0f}%`\n\n"
        f"💡 *המלצה:*\n{alert.action_recommendation}\n\n"
        f"🕐 _{alert.timestamp.strftime('%H:%M UTC')}_"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Telegram alert failed for %s: %s %s", alert.ticker, resp.status, body[:200])
                else:
                    logger.info("Alert sent for %s — catalyst=%s score=%d",
                                alert.ticker, alert.catalyst_type, alert.catalyst_score)
    except Exception as e:
        logger.error("Failed to send Telegram alert for %s: %s", alert.ticker, e)


# ══════════════════════════════════════════════════════════════════════════════
# Log alert to MongoDB
# ══════════════════════════════════════════════════════════════════════════════

def _log_alert(alert: NewsAlert) -> None:
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        db["news_alerts_log"].insert_one({
            "ticker": alert.ticker,
            "headline": alert.headline,
            "catalyst_type": alert.catalyst_type,
            "catalyst_score": alert.catalyst_score,
            "expected_move": alert.expected_move,
            "magnitude": alert.magnitude,
            "action_recommendation": alert.action_recommendation,
            "iv_rank": alert.iv_rank,
            "timestamp": alert.timestamp,
            "source": alert.source,
        })
    except Exception as e:
        logger.debug("Failed to log alert to MongoDB: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# Per-ticker scan
# ══════════════════════════════════════════════════════════════════════════════

async def scan_news_for_ticker(ticker: str) -> Optional[NewsAlert]:
    """
    Scan Perplexity for breaking news on a single ticker.
    Returns NewsAlert if catalyst found above threshold, else None.
    """
    from app.services.perplexity_service import PerplexityService
    from app.services.iv_calculator import get_iv_rank

    perp = PerplexityService()
    if not perp.is_available():
        logger.debug("Perplexity unavailable — skipping %s", ticker)
        return None

    try:
        query = (
            f"Is there any BREAKING NEWS, major catalyst, or significant development "
            f"for {ticker} stock TODAY? "
            f"Include: earnings, FDA, acquisitions, analyst changes, government contracts, "
            f"short squeeze, insider trading, investigations. "
            f"If NO major news today, respond with exactly: NO_CATALYST. "
            f"Otherwise give headline + one sentence detail."
        )

        raw = await asyncio.to_thread(perp.search, query, 600)

        if not raw or "NO_CATALYST" in raw.upper() or len(raw.strip()) < 20:
            return None

        catalyst_type, score = _detect_catalyst_type(raw)

        if score < ALERT_THRESHOLD:
            logger.debug("%s: news found but score=%d < threshold=%d", ticker, score, ALERT_THRESHOLD)
            return None

        # Extract headline (first sentence)
        headline = raw.split(".")[0].strip()
        if len(headline) < 10:
            headline = raw[:120].strip()

        if _is_duplicate(ticker, headline):
            logger.debug("%s: duplicate alert suppressed", ticker)
            return None

        iv_rank = await asyncio.to_thread(get_iv_rank, ticker)
        expected_move, magnitude = _estimate_move(catalyst_type, score)
        action = _recommend_action(catalyst_type, score, iv_rank)

        alert = NewsAlert(
            ticker=ticker,
            headline=headline,
            catalyst_type=catalyst_type,
            catalyst_score=score,
            expected_move=expected_move,
            magnitude=magnitude,
            action_recommendation=action,
            iv_rank=iv_rank,
            raw_text=raw,
        )

        await _send_telegram_alert(alert)
        _log_alert(alert)
        return alert

    except Exception as e:
        logger.warning("scan_news_for_ticker(%s) failed: %s", ticker, e)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Full watchlist scan
# ══════════════════════════════════════════════════════════════════════════════

async def run_news_scan_job() -> list[NewsAlert]:
    """Scan all watchlist tickers for breaking catalysts."""
    watchlist = _get_watchlist()
    logger.info("[NewsAlert] Scanning %d tickers: %s", len(watchlist), watchlist)

    alerts = []
    for ticker in watchlist:
        try:
            alert = await scan_news_for_ticker(ticker)
            if alert:
                alerts.append(alert)
                logger.info("[NewsAlert] 🚨 %s — %s (score=%d)", ticker, alert.catalyst_type, alert.catalyst_score)
        except Exception as e:
            logger.warning("[NewsAlert] %s scan error: %s", ticker, e)
        await asyncio.sleep(2)  # rate limit — 2s between tickers

    logger.info("[NewsAlert] Scan complete — %d alerts sent", len(alerts))
    return alerts


def run_news_scan_sync() -> None:
    """Sync wrapper for APScheduler — runs the async scan in a new event loop."""
    try:
        asyncio.run(run_news_scan_job())
    except Exception as e:
        logger.error("[NewsAlert] run_news_scan_sync failed: %s", e)
