"""
live_monitor.py — 24/7 Proactive Intelligence Monitor
======================================================

The agent never sleeps. It runs continuously in the background
and sends you information BEFORE you ask.

Every 15 minutes (market hours 16:30-23:00 Israel):
  - Price alerts (big moves >3%)
  - IV spikes (>60% rank = sell premium opportunity)
  - Earnings warnings (7/3/1 day ahead)
  - News catalysts for watchlist

Every morning 09:00 Israel:
  - Market overview + GEX levels + economic calendar

Every evening 23:30 Israel:
  - Day summary + tomorrow's key events

Every 30 minutes (market hours):
  - SEC filings / Fed updates / unusual options flow
"""

import asyncio
import logging
import os
import time
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)

# Dedup cache: don't send the same alert within 4 hours
_sent_cache: dict = {}
_CACHE_TTL = 4 * 3600


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_market_hours() -> bool:
    """True during US market hours in Israel time (16:30–23:00, Mon–Fri)."""
    now = datetime.now()
    hour = now.hour + now.minute / 60
    return now.weekday() < 5 and 16.5 <= hour <= 23.0


def _is_duplicate(key: str) -> bool:
    """Return True if this alert was already sent in the last 4 hours."""
    now = time.time()
    if key in _sent_cache and now - _sent_cache[key] < _CACHE_TTL:
        return True
    _sent_cache[key] = now
    return False


def _send_telegram(text: str) -> bool:
    """Send Telegram message via existing notify_trade infrastructure."""
    try:
        from app.agent.telegram_bot import notify_trade
        notify_trade(text)
        return True
    except Exception:
        # Fallback: direct requests call
        token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return False
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            return True
        except Exception as e:
            logger.debug("Telegram send failed: %s", e)
            return False


async def _send_proactive_message(text: str) -> bool:
    """Async wrapper — sends Telegram message in a thread."""
    return await asyncio.to_thread(_send_telegram, text)


def _get_watchlist() -> list[str]:
    """Get Haim's watchlist from MongoDB profile."""
    try:
        from app.services.memory_engine import MemoryEngine
        profile = MemoryEngine().get_profile()
        return profile.get("watchlist", ["NVDA", "AAPL", "TSLA", "AMZN", "SPY", "QQQ"])
    except Exception:
        return ["NVDA", "AAPL", "TSLA", "AMZN", "SPY", "QQQ", "META", "PLTR"]


def _search_perplexity(query: str, max_tokens: int = 150) -> str:
    """Quick Perplexity search — synchronous."""
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
                    {"role": "system", "content": "Be very concise. 2-3 sentences max."},
                    {"role": "user", "content": query},
                ],
                "max_tokens": max_tokens,
                "search_recency_filter": "day",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.debug("Perplexity search failed: %s", e)
    return ""


# ── Monitor Jobs ──────────────────────────────────────────────────────────────

async def check_price_moves():
    """Alert on big price moves in watchlist (>3% in one session)."""
    watchlist = _get_watchlist()
    try:
        import yfinance as yf
        for ticker in watchlist[:10]:
            try:
                hist = yf.Ticker(ticker).history(period="2d")
                if hist.empty or len(hist) < 2:
                    continue
                prev_close = float(hist["Close"].iloc[-2])
                curr_price = float(hist["Close"].iloc[-1])
                change_pct = (curr_price / prev_close - 1) * 100

                if abs(change_pct) >= 3.0:
                    alert_key = f"move_{ticker}_{date.today()}"
                    if not _is_duplicate(alert_key):
                        direction = "📈 עולה" if change_pct > 0 else "📉 יורד"
                        reason = await asyncio.to_thread(
                            _search_perplexity,
                            f"Why is {ticker} stock moving {change_pct:+.1f}% today? "
                            f"What is the specific catalyst?",
                        )
                        msg = (
                            f"⚡ *תנועה חדה — {ticker}*\n"
                            f"{direction} `{change_pct:+.1f}%` | מחיר: `${curr_price:.2f}`\n\n"
                            f"💬 *למה זה זז:*\n{reason}\n\n"
                            f"💡 רוצה ניתוח? שלח: `מה דעתך על {ticker}?`"
                        )
                        await _send_proactive_message(msg)
                        logger.info("Price move alert: %s %+.1f%%", ticker, change_pct)
            except Exception:
                continue
    except Exception as e:
        logger.debug("check_price_moves failed: %s", e)


async def check_iv_spikes():
    """Alert when IV Rank spikes above 60% — good for selling premium."""
    watchlist = _get_watchlist()
    try:
        from app.services.realtime_market_data import get_realtime_iv_data
        for ticker in watchlist[:8]:
            try:
                iv = get_realtime_iv_data(ticker)
                if not iv or iv.current_price <= 0:
                    continue
                if iv.iv_rank >= 60:
                    alert_key = f"iv_spike_{ticker}_{date.today()}"
                    if not _is_duplicate(alert_key):
                        strategy = "Iron Condor" if iv.iv_rank >= 70 else "Bull Put Spread"
                        msg = (
                            f"🔥 *IV Spike — {ticker}*\n"
                            f"IV Rank: `{iv.iv_rank:.0f}%` — פרמיה עשירה!\n"
                            f"מחיר: `${iv.current_price:.2f}`\n"
                            f"Expected Move: `±${iv.expected_move_30d}`\n\n"
                            f"💡 *הזדמנות:* {strategy}\n"
                            f"שלח `/scan {ticker}` לניתוח מלא"
                        )
                        await _send_proactive_message(msg)
                        logger.info("IV spike alert: %s %.0f%%", ticker, iv.iv_rank)
            except Exception:
                continue
    except Exception as e:
        logger.debug("check_iv_spikes failed: %s", e)


async def check_earnings_warnings():
    """Warn about upcoming earnings in watchlist (7/3/1 days ahead)."""
    watchlist = _get_watchlist()
    try:
        import yfinance as yf
        today = date.today()
        for ticker in watchlist[:10]:
            try:
                cal = yf.Ticker(ticker).calendar
                if cal is None or cal.empty or "Earnings Date" not in cal.index:
                    continue
                earn = cal.loc["Earnings Date"]
                if hasattr(earn, "iloc"):
                    earn = earn.iloc[0]
                if hasattr(earn, "date"):
                    earn = earn.date()
                days = (earn - today).days
                if days in (7, 3, 1):
                    alert_key = f"earnings_{ticker}_{days}d"
                    if not _is_duplicate(alert_key):
                        urgency = "🚨" if days <= 3 else "⚠️"
                        msg = (
                            f"{urgency} *Earnings בעוד {days} ימים — {ticker}*\n"
                            f"תאריך: `{earn.strftime('%d/%m/%Y')}`\n\n"
                            f"⚠️ *זכור:* אל תמכור אופציות לפני Earnings!\n"
                            f"שקול: Long Straddle לפני, מכור פרמיה אחרי IV Crush\n\n"
                            f"שלח `/deepscan {ticker}` לניתוח מלא"
                        )
                        await _send_proactive_message(msg)
                        logger.info("Earnings warning sent: %s in %d days", ticker, days)
            except Exception:
                continue
    except Exception as e:
        logger.debug("check_earnings_warnings failed: %s", e)


async def check_news_catalysts():
    """Scan for major news catalysts in top watchlist stocks."""
    watchlist = _get_watchlist()
    today = date.today().strftime("%B %d, %Y")
    for ticker in watchlist[:5]:
        try:
            news = await asyncio.to_thread(
                _search_perplexity,
                f"Is there any major news for {ticker} stock today {today}? "
                f"Contracts, M&A, FDA, partnerships, earnings surprise? "
                f"Only report if truly significant. Say 'nothing significant' if not.",
            )
            if news and "nothing significant" not in news.lower() and len(news) > 40:
                alert_key = f"news_{ticker}_{hash(news[:40])}"
                if not _is_duplicate(alert_key):
                    msg = (
                        f"📰 *חדשות — {ticker}*\n\n"
                        f"{news}\n\n"
                        f"💡 רוצה ניתוח? שלח: `מה דעתך על {ticker}?`"
                    )
                    await _send_proactive_message(msg)
                    logger.info("News catalyst alert: %s", ticker)
            await asyncio.sleep(2)  # Rate-limit Perplexity
        except Exception:
            continue


async def send_morning_briefing():
    """Send morning market briefing at 09:00 Israel time."""
    today = date.today().strftime("%d/%m/%Y")
    day_names = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
    day_name = day_names[date.today().weekday()]

    # TradingView market snapshot
    market_text = ""
    try:
        from app.services.tradingview_service import get_market_context_for_agent1
        market_text = get_market_context_for_agent1() or ""
    except Exception:
        pass

    # Macro calendar from Perplexity
    macro = await asyncio.to_thread(
        _search_perplexity,
        f"Key economic events and earnings today {date.today().strftime('%B %d, %Y')}: "
        f"FOMC, CPI, NFP, major S&P500 earnings. Be specific with times.",
        200,
    )

    # GEX levels
    gex_text = ""
    try:
        from app.services.gex_calculator import calculate_gex
        gex = calculate_gex("SPY")
        if gex:
            regime_emoji = "🟢" if gex.gamma_regime == "POSITIVE" else "🔴"
            gex_text = (
                f"\n📐 *GEX — SPY:*\n"
                f"Zero Gamma: `${gex.zero_gamma}` | "
                f"Call Wall: `${gex.call_wall}` | "
                f"Put Wall: `${gex.put_wall}`\n"
                f"Regime: {regime_emoji} {gex.gamma_regime}"
            )
    except Exception:
        pass

    msg = (
        f"🌅 *בוקר טוב חיים! — {day_name} {today}*\n"
        f"{'━'*28}\n\n"
        f"{market_text}\n"
        f"{gex_text}\n\n"
        f"📅 *לוח אירועים היום:*\n{macro}\n\n"
        f"{'━'*28}\n"
        f"💡 שלח `/regime` לניתוח שוק מלא\n"
        f"📊 שלח `/strategist` להמלצות עסקאות"
    )
    await _send_proactive_message(msg)
    logger.info("Morning briefing sent")


async def send_evening_summary():
    """Send evening market summary at 23:30 Israel time."""
    today = date.today().strftime("%d/%m/%Y")

    summary = await asyncio.to_thread(
        _search_perplexity,
        f"Biggest stock market moves and news today {date.today().strftime('%B %d, %Y')}: "
        f"top 3 movers, why they moved, what to watch tomorrow.",
        200,
    )
    tomorrow = (date.today() + timedelta(days=1)).strftime("%B %d, %Y")
    tomorrow_events = await asyncio.to_thread(
        _search_perplexity,
        f"Major earnings and economic events tomorrow {tomorrow}. List the most important.",
    )

    msg = (
        f"🌙 *סיכום יום — {today}*\n"
        f"{'━'*28}\n\n"
        f"📊 *מה קרה היום:*\n{summary}\n\n"
        f"📅 *מחר לשים לב:*\n{tomorrow_events}\n\n"
        f"לילה טוב! 🌙"
    )
    await _send_proactive_message(msg)
    logger.info("Evening summary sent")


async def crawl_financial_sites():
    """
    Proactively crawl for SEC filings, Fed updates, and unusual options flow.
    Runs every 30 minutes during market hours.
    """
    sites = [
        ("SEC Filings", "latest SEC 8-K filings today for major tech stocks NVDA AAPL MSFT AMZN"),
        ("Fed Updates", "any Federal Reserve statements or speeches today"),
        ("Options Flow", "unusual options activity or large dark pool prints today large cap stocks"),
    ]
    for site_name, query in sites:
        try:
            content = await asyncio.to_thread(_search_perplexity, query)
            if content and len(content) > 50:
                alert_key = f"crawl_{site_name}_{hash(content[:40])}"
                if not _is_duplicate(alert_key):
                    msg = f"🕷️ *{site_name} — עדכון אוטומטי*\n\n{content}"
                    await _send_proactive_message(msg)
            await asyncio.sleep(3)
        except Exception:
            continue


# ── Orchestrated Scans ────────────────────────────────────────────────────────

async def run_15min_scan():
    """All 15-minute checks — runs during market hours."""
    if not _is_market_hours():
        logger.debug("Market closed — skipping 15min scan")
        return
    logger.info("Running 15min market scan...")
    await asyncio.gather(
        check_price_moves(),
        check_iv_spikes(),
        check_news_catalysts(),
        check_earnings_warnings(),
        return_exceptions=True,
    )


async def run_30min_crawl():
    """Web crawl — runs during market hours."""
    if not _is_market_hours():
        return
    await crawl_financial_sites()


# ── Sync wrappers for APScheduler ─────────────────────────────────────────────

def run_15min_scan_sync():
    try:
        asyncio.run(run_15min_scan())
    except Exception as e:
        logger.error("15min scan failed: %s", e)


def run_30min_crawl_sync():
    try:
        asyncio.run(run_30min_crawl())
    except Exception as e:
        logger.error("30min crawl failed: %s", e)


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
