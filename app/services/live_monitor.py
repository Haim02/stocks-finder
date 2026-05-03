"""
live_monitor.py — Smart Alert System v2
========================================

Changes from v1:
- Runs every 2 HOURS (not 15 minutes)
- Only Mon-Fri, 10:00-22:00 Israel time
- Only sends HIGH-VALUE alerts (not every news)
- Focuses on: SPY/QQQ/SPX + S&P 500 big movers
- Geopolitical events that move markets
- NO Fed talk unless rate decision
- Saves every alert to MongoDB for XGBoost training
"""

import asyncio
import logging
import os
import time
from datetime import datetime, date

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Only these tickers get monitored
CORE_TICKERS = ["SPY", "QQQ"]
SP500_MEGA_CAPS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA",
    "BRK-B", "JPM", "V", "UNH", "XOM", "LLY", "JNJ", "MA",
    "HD", "PG", "COST", "AVGO", "MRK",
]

MIN_MOVE_PCT = 3.0

HIGH_VALUE_KEYWORDS = [
    "acqui",  # acquisition, acquires, acquired, acquiring
    "merger", "buyout", "takeover",
    "contract", "pentagon", "government deal",
    "fda approv",  # fda approved, fda approval
    "earnings beat", "revenue beat", "guidance raised",
    "partnership", "strategic alliance",
    "war", "military", "conflict", "sanctions", "tariff",
    "bankruptcy", "default", "crisis",
    "ai deal", "chip ban", "export control",
    "rate cut", "rate hike",
    "לרכוש", "הסכם", "עסקה", "מלחמה", "סנקציות",
]

IGNORE_KEYWORDS = [
    "fed speak", "fed speech", "comments", "remarks",
    "analyst says", "analyst thinks", "could", "might",
    "speculation", "rumor", "unconfirmed",
    "powell said", "fed member",
]

_sent_cache: dict = {}
_CACHE_TTL = 8 * 3600


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_active_hours() -> bool:
    """Only Mon-Fri, 10:00-22:00 Israel time."""
    now = datetime.now()
    return now.weekday() < 5 and 10 <= now.hour < 22


def _is_duplicate(key: str) -> bool:
    if key in _sent_cache and time.time() - _sent_cache[key] < _CACHE_TTL:
        return True
    _sent_cache[key] = time.time()
    return False


def _is_high_value(text: str) -> tuple[bool, str]:
    """Returns (is_high_value, reason). Only True for genuinely important news."""
    text_lower = text.lower()
    for kw in IGNORE_KEYWORDS:
        if kw in text_lower:
            return False, f"filtered: {kw}"
    for kw in HIGH_VALUE_KEYWORDS:
        if kw in text_lower:
            return True, kw
    import re
    for match in re.findall(r'(\d+\.?\d*)\s*%', text):
        if float(match) >= 5:
            return True, f"big move: {match}%"
    return False, "not significant"


def _save_alert_to_db(ticker: str, alert_type: str,
                      headline: str, action: str,
                      price_at_alert: float = 0.0):
    """Save every alert to MongoDB for XGBoost training."""
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        db["alert_training_data"].insert_one({
            "ticker":           ticker,
            "alert_type":       alert_type,
            "headline":         headline[:200],
            "action":           action,
            "price_at_alert":   price_at_alert,
            "price_24h_later":  None,
            "price_1w_later":   None,
            "was_correct":      None,
            "timestamp":        datetime.now(),
        })
        logger.debug("Alert saved to DB: %s %s", ticker, alert_type)
    except Exception as e:
        logger.debug("Failed to save alert to DB: %s", e)


def _update_alert_outcomes():
    """Fill in 24h price outcomes for past alerts. Called during /train."""
    try:
        import yfinance as yf
        from app.data.mongo_client import MongoDB
        from datetime import timedelta

        db = MongoDB.get_db()
        now = datetime.now()

        alerts_24h = list(db["alert_training_data"].find({
            "price_24h_later": None,
            "timestamp": {
                "$lt":  now - timedelta(hours=23),
                "$gt":  now - timedelta(hours=48),
            },
        }))

        for alert in alerts_24h:
            ticker   = alert.get("ticker", "")
            price_at = alert.get("price_at_alert", 0)
            if not ticker or not price_at:
                continue
            try:
                hist = yf.Ticker(ticker).history(period="3d")
                if not hist.empty:
                    current    = float(hist["Close"].iloc[-1])
                    change_pct = (current / price_at - 1) * 100
                    action     = alert.get("action", "").lower()
                    was_correct = None
                    if "bull" in action or "call" in action:
                        was_correct = change_pct > 1.0
                    elif "bear" in action or "put" in action:
                        was_correct = change_pct < -1.0
                    db["alert_training_data"].update_one(
                        {"_id": alert["_id"]},
                        {"$set": {
                            "price_24h_later": current,
                            "change_24h_pct":  round(change_pct, 2),
                            "was_correct":     was_correct,
                        }},
                    )
            except Exception:
                continue

        logger.info("Updated %d alert outcomes", len(alerts_24h))
    except Exception as e:
        logger.debug("Update alert outcomes failed: %s", e)


def _send_telegram_sync(text: str) -> bool:
    """Send Telegram message synchronously via requests."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        import requests
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        logger.debug("Telegram send failed: %s", e)
        return False


async def _send_alert(text: str) -> bool:
    """Async wrapper around the synchronous Telegram send."""
    return await asyncio.to_thread(_send_telegram_sync, text)


def _search_perplexity(query: str) -> str:
    """Quick targeted Perplexity search."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        return ""
    try:
        import requests
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Report ONLY significant financial news. "
                            "If nothing major happened, say NOTHING_SIGNIFICANT. "
                            "Be concise: 2-3 sentences max."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                "max_tokens": 150,
                "search_recency_filter": "day",
            },
            timeout=8,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""


def _translate_to_hebrew(text: str) -> str:
    """Translate to Hebrew if needed. Skips if already >25% Hebrew."""
    if not text:
        return text
    hebrew_chars = sum(1 for c in text if "א" <= c <= "ת")
    if hebrew_chars / max(len(text), 1) > 0.25:
        return text
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content":
                "תרגם לעברית בצורה טבעית. שמור מונחים: SPY, QQQ, IV, DTE, "
                "EPS, GDP, M&A, Fed rate, S&P 500, NASDAQ. רק תרגם:\n\n" + text
            }],
        )
        return resp.content[0].text.strip()
    except Exception:
        return text


# ── Core Scan Functions ───────────────────────────────────────────────────────

async def check_big_price_moves():
    """Alert only on moves > 3% in core tickers + top mega-caps."""
    import yfinance as yf

    all_tickers = CORE_TICKERS + SP500_MEGA_CAPS[:10]

    for ticker in all_tickers:
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if hist.empty or len(hist) < 2:
                continue

            prev       = float(hist["Close"].iloc[-2])
            curr       = float(hist["Close"].iloc[-1])
            change_pct = (curr / prev - 1) * 100

            if abs(change_pct) < MIN_MOVE_PCT:
                continue

            alert_key = f"move_{ticker}_{date.today()}"
            if _is_duplicate(alert_key):
                continue

            direction = "📈 עלה" if change_pct > 0 else "📉 ירד"

            reason_raw = await asyncio.to_thread(
                _search_perplexity,
                f"Why did {ticker} move {change_pct:+.1f}% today? "
                f"What is the specific catalyst? M&A, earnings, contract, news?",
            )

            if not reason_raw or "NOTHING_SIGNIFICANT" in reason_raw:
                continue

            is_hv, kw = _is_high_value(reason_raw)
            if not is_hv and abs(change_pct) < 5.0:
                logger.debug("Skipping %s move — not high value (%s)", ticker, kw)
                continue

            reason_heb = await asyncio.to_thread(_translate_to_hebrew, reason_raw)

            xgb_note = ""
            try:
                from app.services.ml_service import predict_confidence
                conf = predict_confidence(ticker)
                if conf:
                    xgb_note = f"\n🤖 XGBoost: `{conf:.0f}%` ביטחון"
            except Exception:
                pass

            action = "📈 Bull Put Spread" if change_pct > 0 else "📉 Bear Call Spread"

            msg = (
                f"⚡ *תנועה חדה — {ticker}*\n"
                f"{'━'*26}\n"
                f"{direction} `{change_pct:+.1f}%` | מחיר: `${curr:.2f}`\n\n"
                f"💬 *מה קרה:*\n{reason_heb}"
                f"{xgb_note}\n\n"
                f"💡 *פעולה אפשרית:* {action}"
            )

            sent = await _send_alert(msg)
            if sent:
                _save_alert_to_db(
                    ticker=ticker,
                    alert_type="PRICE_MOVE",
                    headline=reason_raw[:200],
                    action=action,
                    price_at_alert=curr,
                )
                logger.info("Price alert sent: %s %+.1f%%", ticker, change_pct)

            await asyncio.sleep(2)

        except Exception as e:
            logger.debug("Price check failed for %s: %s", ticker, e)


async def check_major_news():
    """Check for HIGH-VALUE news only — M&A, contracts, geopolitical, earnings beats."""
    today = date.today().strftime("%B %d, %Y")

    query = (
        f"Major market-moving news today {today}. "
        f"ONLY include: M&A deals, major contracts (Pentagon, government), "
        f"FDA approvals, major earnings beats, geopolitical events (wars, sanctions, tariffs). "
        f"SKIP: Fed speeches, analyst opinions, speculation. "
        f"Format: TICKER: what happened. If nothing major, say NOTHING_SIGNIFICANT."
    )

    news_raw = await asyncio.to_thread(_search_perplexity, query)

    if not news_raw or "NOTHING_SIGNIFICANT" in news_raw:
        logger.debug("No major news today")
        return

    is_hv, kw = _is_high_value(news_raw)
    if not is_hv:
        logger.debug("News not high value: %s", kw)
        return

    alert_key = f"major_news_{hash(news_raw[:40])}"
    if _is_duplicate(alert_key):
        return

    news_heb = await asyncio.to_thread(_translate_to_hebrew, news_raw)

    msg = (
        f"📰 *חדשות חשובות — {today}*\n"
        f"{'━'*26}\n\n"
        f"{news_heb}\n\n"
        f"💡 רוצה ניתוח? שאל אותי ישירות"
    )

    sent = await _send_alert(msg)
    if sent:
        _save_alert_to_db(
            ticker="MARKET",
            alert_type="MAJOR_NEWS",
            headline=news_raw[:200],
            action="general",
        )


async def check_geopolitical():
    """Check for geopolitical events that move markets."""
    today = date.today().strftime("%B %d, %Y")

    query = (
        f"Any major geopolitical events today {today} that could move "
        f"stock markets significantly? Wars, sanctions, tariffs, trade deals, "
        f"oil supply disruptions. If nothing major, say NOTHING_SIGNIFICANT."
    )

    news_raw = await asyncio.to_thread(_search_perplexity, query)

    if not news_raw or "NOTHING_SIGNIFICANT" in news_raw:
        return

    alert_key = f"geo_{hash(news_raw[:40])}"
    if _is_duplicate(alert_key):
        return

    news_heb = await asyncio.to_thread(_translate_to_hebrew, news_raw)

    msg = (
        f"🌍 *אירוע גיאופוליטי*\n"
        f"{'━'*26}\n\n"
        f"{news_heb}\n\n"
        f"📊 *השפעה צפויה:* שאל `/regime` לניתוח מלא"
    )

    sent = await _send_alert(msg)
    if sent:
        _save_alert_to_db(
            ticker="GEO",
            alert_type="GEOPOLITICAL",
            headline=news_raw[:200],
            action="monitor",
        )


async def check_iv_spikes():
    """Alert when IV Rank > 70% — genuinely attractive for premium selling."""
    try:
        from app.services.realtime_market_data import get_realtime_iv_data

        for ticker in CORE_TICKERS + SP500_MEGA_CAPS[:8]:
            try:
                iv_data = get_realtime_iv_data(ticker)
                if not iv_data or iv_data.current_price <= 0:
                    continue
                if iv_data.iv_rank < 70:
                    continue

                alert_key = f"iv_{ticker}_{date.today()}"
                if _is_duplicate(alert_key):
                    continue

                msg = (
                    f"🔥 *IV גבוה מאוד — {ticker}*\n"
                    f"IV Rank: `{iv_data.iv_rank:.0f}%` | "
                    f"מחיר: `${iv_data.current_price:.2f}`\n"
                    f"Expected Move: `±${iv_data.expected_move_30d}`\n\n"
                    f"💡 שקול: Iron Condor או Bull Put Spread\n"
                    f"שלח `/scan {ticker}` לניתוח"
                )

                sent = await _send_alert(msg)
                if sent:
                    _save_alert_to_db(
                        ticker=ticker,
                        alert_type="IV_SPIKE",
                        headline=f"IV Rank {iv_data.iv_rank:.0f}%",
                        action="Iron Condor",
                        price_at_alert=iv_data.current_price,
                    )

            except Exception:
                continue

    except Exception as e:
        logger.debug("IV spike check failed: %s", e)


# ── Main 2-Hour Scan ──────────────────────────────────────────────────────────

async def run_2hour_scan():
    """Main scan — runs every 2 hours during active hours."""
    if not _is_active_hours():
        logger.debug("Outside active hours — skipping scan")
        return

    logger.info("Running 2-hour smart scan...")

    await asyncio.gather(
        check_big_price_moves(),
        check_major_news(),
        check_geopolitical(),
        check_iv_spikes(),
        return_exceptions=True,
    )

    logger.info("2-hour scan complete")


async def send_morning_briefing():
    """Send morning briefing at 09:00 Israel time."""
    import yfinance as yf
    today    = date.today().strftime("%d/%m/%Y")
    day_names = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    day_name  = day_names[date.today().weekday()]

    market_lines = []
    for symbol, label in [("SPY", "SPY"), ("QQQ", "QQQ"), ("^VIX", "VIX"), ("GLD", "GLD")]:
        try:
            hist = yf.Ticker(symbol).history(period="2d")
            if not hist.empty and len(hist) >= 2:
                price = float(hist["Close"].iloc[-1])
                prev  = float(hist["Close"].iloc[-2])
                chg   = (price / prev - 1) * 100
                emoji = "📈" if chg >= 0 else "📉"
                market_lines.append(f"{emoji} {label}: `${price:.2f}` ({chg:+.1f}%)")
        except Exception:
            continue

    market_text = "\n".join(market_lines)

    today_str  = date.today().strftime("%B %d, %Y")
    events_raw = await asyncio.to_thread(
        _search_perplexity,
        f"Key market events today {today_str}: "
        f"major earnings reports, economic data (CPI/NFP/GDP), "
        f"Fed rate decisions only (not speeches). "
        f"List only what's actually happening today.",
    )
    events_heb = (
        await asyncio.to_thread(_translate_to_hebrew, events_raw)
        if events_raw else "אין אירועים מרכזיים היום"
    )

    msg = (
        f"🌅 *בוקר טוב חיים! — {day_name} {today}*\n"
        f"{'━'*28}\n\n"
        f"📊 *שווקים:*\n{market_text}\n\n"
        f"{'━'*28}\n"
        f"📅 *היום לשים לב:*\n{events_heb}\n\n"
        f"{'━'*28}\n"
        f"/regime — ניתוח מלא | /strategist — עסקאות"
    )

    await _send_alert(msg)
    logger.info("Morning briefing sent")


async def send_evening_summary():
    """Send evening summary at 22:30 Israel time."""
    today = date.today().strftime("%d/%m/%Y")

    summary_raw = await asyncio.to_thread(
        _search_perplexity,
        "Top 3 stock market moves today and why. "
        "What should traders watch tomorrow? Be brief.",
    )
    summary_heb = (
        await asyncio.to_thread(_translate_to_hebrew, summary_raw)
        if summary_raw else "אין סיכום זמין"
    )

    msg = (
        f"🌙 *סיכום יום — {today}*\n"
        f"{'━'*28}\n\n"
        f"{summary_heb}"
    )

    await _send_alert(msg)
    logger.info("Evening summary sent")


# ── Sync wrappers for APScheduler ─────────────────────────────────────────────

def run_2hour_scan_sync():
    try:
        asyncio.run(run_2hour_scan())
    except Exception as e:
        logger.error("2h scan failed: %s", e)


def run_morning_briefing_sync():
    try:
        asyncio.run(send_morning_briefing())
    except Exception as e:
        logger.error("Morning briefing failed: %s", e)


def run_evening_summary_sync():
    try:
        asyncio.run(send_evening_summary())
    except Exception as e:
        logger.error("Evening summary failed: %s", e)


def update_alert_outcomes_sync():
    """Called during /train to update alert accuracy."""
    _update_alert_outcomes()
