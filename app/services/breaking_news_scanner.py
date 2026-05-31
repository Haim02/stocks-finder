"""
breaking_news_scanner.py — Breaking News Real-Time Scanner
===========================================================

Runs every 5 minutes during market hours (Mon-Fri 16:30-23:00 Israel).
Specifically scans for HIGH-IMPACT breaking news that moves markets
immediately — like the Iran-US deal that spiked SPX 50+ points.

Sources: Axios RSS (fastest), Perplexity, yfinance news
"""

import logging
import time
import os
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# Cache to prevent duplicate alerts
_sent_cache: dict = {}
_CACHE_TTL = 2 * 3600  # 2 hours

# Keywords that cause IMMEDIATE market moves
BREAKING_KEYWORDS = {
    # Geopolitical — massive market movers
    "iran deal": 95,
    "iran nuclear": 95,
    "iran agreement": 95,
    "us iran": 90,
    "ceasefire": 90,
    "peace deal": 88,
    "war declared": 95,
    "military strike": 92,
    "nuclear": 88,
    "sanctions lifted": 85,
    "trade deal": 88,
    "tariff removed": 85,
    "tariff cut": 85,
    "trade war": 82,
    "china deal": 88,
    "russia": 80,
    "oil embargo": 88,
    "strait of hormuz": 90,
    "opec": 82,

    # Fed — immediate rate decisions only
    "rate cut": 90,
    "rate hike": 90,
    "emergency meeting": 92,
    "fed cuts": 90,
    "fed hikes": 90,

    # Corporate — immediate movers
    "acquisition": 82,
    "merger": 82,
    "buyout": 85,
    "takeover bid": 85,
    "fda approved": 88,
    "fda approval": 88,
    "bankruptcy": 88,
    "fraud": 85,

    # AI/Tech mega news
    "openai": 75,
    "nvidia deal": 82,
    "ai ban": 85,
    "chip ban": 85,
    "export control": 80,
}

# Keywords to IGNORE completely
IGNORE_KEYWORDS = [
    "analyst says", "could", "might", "expected to",
    "sources say maybe", "rumor", "speculation",
    "powell speech", "fed member says",
]


def _is_market_hours() -> bool:
    """Mon-Fri 16:30-23:00 Israel time."""
    now = datetime.now()
    hour = now.hour + now.minute / 60
    return now.weekday() < 5 and 16.5 <= hour <= 23.0


def _is_duplicate(key: str) -> bool:
    if key in _sent_cache:
        if time.time() - _sent_cache[key] < _CACHE_TTL:
            return True
    _sent_cache[key] = time.time()
    return False


def _score_headline(text: str) -> tuple[int, str]:
    """Score a headline by market impact. Returns (score, keyword)."""
    text_lower = text.lower()

    # Check ignore list first
    for ig in IGNORE_KEYWORDS:
        if ig in text_lower:
            return 0, ""

    best_score = 0
    best_kw = ""
    for kw, score in BREAKING_KEYWORDS.items():
        if kw in text_lower and score > best_score:
            best_score = score
            best_kw = kw

    return best_score, best_kw


def _fetch_axios_breaking() -> list[dict]:
    """Fetch latest Axios headlines — fastest source."""
    import requests
    from xml.etree import ElementTree as ET

    feeds = [
        "https://www.axios.com/feeds/feed.rss",
        "https://api.axios.com/feed/business",
        "https://api.axios.com/feed/politics-policy",
        "https://api.axios.com/feed/world",
    ]

    articles = []
    headers = {"User-Agent": "Mozilla/5.0 (NewsBot/2.0)"}

    for url in feeds:
        try:
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if not channel:
                continue

            for item in channel.findall("item")[:8]:
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                link = item.findtext("link", "")
                pub = item.findtext("pubDate", "")

                if title:
                    articles.append({
                        "title": title,
                        "desc": desc[:150] if desc else "",
                        "url": link,
                        "pub": pub,
                        "source": "Axios",
                    })
        except Exception:
            continue

    return articles


def _fetch_perplexity_breaking() -> list[dict]:
    """Ask Perplexity for breaking news in last 30 minutes."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        return []

    try:
        import requests
        today = date.today().strftime("%B %d, %Y")
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You monitor breaking financial news. "
                            "Report ONLY news from the LAST 30 MINUTES. "
                            "If nothing significant: say NOTHING_NEW. "
                            "Format: HEADLINE | IMPACT (HIGH/MEDIUM) | TICKERS AFFECTED"
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Breaking market news right now on {today}? "
                            f"Geopolitical deals, rate decisions, major M&A, FDA. "
                            f"Last 30 minutes only."
                        )
                    }
                ],
                "max_tokens": 200,
                "search_recency_filter": "hour",
            },
            timeout=8,
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if "NOTHING_NEW" in text:
                return []
            return [{"title": text, "desc": "", "url": "", "source": "Perplexity"}]
    except Exception:
        pass
    return []


def _translate_to_hebrew(text: str) -> str:
    """Translate to Hebrew using Claude."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content":
                f"תרגם לעברית קצר ומדויק. שמור שמות: Iran, US, Fed, OPEC, SPX:\n{text}"
            }]
        )
        return resp.content[0].text.strip()
    except Exception:
        return text


def _build_options_action(score: int, keyword: str, spy_price: float) -> str:
    """Suggest immediate options action based on news type."""

    if any(w in keyword for w in ["iran", "ceasefire", "peace", "deal", "tariff cut"]):
        return (
            f"פעולה מומלצת:\n"
            f"🔵 Long Call SPY (תנועה שורית מהירה)\n"
            f"Strike: ATM או +1% | DTE: היום עד שבוע\n"
            f"כניסה מהירה — IV יעלה בקרוב!"
        )
    elif any(w in keyword for w in ["war", "strike", "nuclear", "crisis"]):
        return (
            f"פעולה מומלצת:\n"
            f"🔴 Long Put SPY (תנועה דובית מהירה)\n"
            f"Strike: ATM או -1% | DTE: היום עד שבוע\n"
            f"אל תמתין — שוק יגיב תוך דקות!"
        )
    elif any(w in keyword for w in ["rate cut", "fed cuts"]):
        return (
            f"פעולה מומלצת:\n"
            f"🔵 Long Call SPY + QQQ\n"
            f"הפחתת ריבית = ראלי מיידי לרוב\n"
            f"IV יזנק — קנה לפני!"
        )
    else:
        return (
            f"פעולה: עקוב אחרי SPY בדקות הקרובות.\n"
            f"אם >+0.5% → Long Call | אם <-0.5% → Long Put"
        )


async def scan_breaking_news():
    """
    Main scanner — runs every 5 minutes.
    Checks Axios + Perplexity for breaking news.
    """
    import asyncio
    import aiohttp
    import yfinance as yf

    if not _is_market_hours():
        return

    logger.debug("Running breaking news scan...")

    # Collect from all sources
    all_articles = []
    all_articles.extend(_fetch_axios_breaking())
    all_articles.extend(_fetch_perplexity_breaking())

    if not all_articles:
        return

    # Get current SPY price for context
    spy_price = 0.0
    try:
        hist = yf.Ticker("SPY").history(period="1d")
        if not hist.empty:
            spy_price = float(hist["Close"].iloc[-1])
    except Exception:
        pass

    # Process each article
    for article in all_articles:
        title = article.get("title", "")
        desc = article.get("desc", "")
        full_text = f"{title} {desc}"
        source = article.get("source", "")

        score, keyword = _score_headline(full_text)

        if score < 80:  # Only very high impact
            continue

        alert_key = f"breaking_{hash(title[:40])}"
        if _is_duplicate(alert_key):
            continue

        # Translate to Hebrew
        title_heb = _translate_to_hebrew(title)
        desc_heb = _translate_to_hebrew(desc) if desc else ""

        # Impact label
        if score >= 90:
            impact = "🚨 השפעה גבוהה מאוד"
        elif score >= 85:
            impact = "⚡ השפעה גבוהה"
        else:
            impact = "⚠️ השפעה בינונית-גבוהה"

        # Options action
        action = _build_options_action(score, keyword, spy_price)

        # Build alert
        url_line = f"\n🔗 {article['url']}" if article.get("url") else ""

        msg = (
            f"🔴 חדשות שוברות — {source}\n"
            f"{'━'*28}\n\n"
            f"{impact}\n"
            f"{title_heb}\n"
            + (f"\n{desc_heb}" if desc_heb else "") +
            f"{url_line}\n\n"
            f"{'━'*28}\n"
            f"{action}\n\n"
            f"SPY כעת: ${spy_price:.2f}"
        )

        # Send alert
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        telegram_chat = os.getenv("TELEGRAM_CHAT_ID", "")

        if telegram_token and telegram_chat:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                        json={
                            "chat_id": telegram_chat,
                            "text": msg,
                            "parse_mode": "Markdown",
                        },
                        timeout=aiohttp.ClientTimeout(total=8)
                    )
                logger.info(
                    "Breaking news alert sent: score=%d kw=%s | %s",
                    score, keyword, title[:60]
                )

                # Save to brain for learning
                try:
                    from app.services.brain_logger import log_interaction
                    log_interaction(
                        interaction_type="alert",
                        content=f"BREAKING: {title}",
                        tickers=["SPY", "QQQ"],
                        strategy="Long Option",
                        price_at_time=spy_price,
                        metadata={"score": score, "keyword": keyword, "source": source}
                    )
                except Exception:
                    pass

            except Exception as e:
                logger.debug("Send alert failed: %s", e)


def scan_breaking_news_sync():
    """Sync wrapper for APScheduler."""
    import asyncio
    try:
        asyncio.run(scan_breaking_news())
    except Exception as e:
        logger.error("Breaking news scan failed: %s", e)
