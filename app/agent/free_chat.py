"""
free_chat.py — Intelligent Free Chat Handler
=============================================

Powers natural Hebrew conversation with Claude.
Feels like talking to Claude/ChatGPT — not a bot.

Data access:
- MEMORY.md / CLAUDE.md (identity + trading knowledge)
- MongoDB (positions, strategies, sentiment, training data)
- yfinance (real-time IV, options chain, stock prices)
- Finviz (screener candidates)
- Perplexity (real-time web search)
- OpenAI (quick facts fallback)
- XGBoost model (confidence scores)
- Agent 1 reports (market regime)
- Agent 2 reports (options ideas)

Commands still supported:
/learn <text>  → append to MEMORY.md
/reset         → clear conversation history
"""

import logging
import os
import re
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

import anthropic
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
CLAUDE_MODEL    = "claude-sonnet-4-5"
MAX_HISTORY     = 30           # longer memory = more natural conversation
MAX_TOKENS      = 2048         # longer responses = more thorough answers
_ROOT           = Path(__file__).parent.parent.parent
MEMORY_PATH     = _ROOT / "MEMORY.md"
CLAUDE_PATH     = _ROOT / "CLAUDE.md"

# Tickers to skip when extracting from text
_SKIP_WORDS = {
    'IV', 'DTE', 'ATM', 'OTM', 'ITM', 'PUT', 'CALL', 'VIX', 'RSI',
    'SMA', 'EMA', 'CSP', 'CC', 'AI', 'OK', 'US', 'API', 'ETF',
    'P&L', 'ROI', 'ROC', 'EPS', 'PE', 'MA', 'BB', 'OR', 'IF',
    'AND', 'THE', 'FOR', 'ARE', 'NOT', 'ALL', 'IB', 'TA',
    'RANK', 'SPY', 'QQQ', 'SPX', 'NDX', 'CEO', 'SEC', 'FDA', 'IPO',
    'TELL', 'WHAT', 'WHEN', 'HOW', 'WHY', 'CAN', 'WILL', 'HAS',
    'STOCK', 'ABOUT', 'FROM', 'WITH', 'THIS', 'THAT', 'JUST',
    'LONG', 'SHORT', 'HIGH', 'LOW', 'OPEN', 'CLOSE', 'GOOD',
    'BEST', 'NEXT', 'LAST', 'WEEK', 'DAY', 'NOW', 'GET', 'SET',
    'ME', 'IS', 'IT', 'IN', 'ON', 'AT', 'BY', 'OF', 'TO',
    'UP', 'AN', 'AS', 'DO', 'GO', 'BE', 'NO', 'SO', 'WE', 'MY',
    'HE', 'IM', 'ITS',
}


# ── System Prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    """Build the full system prompt from CLAUDE.md + MEMORY.md."""
    parts = []

    if CLAUDE_PATH.exists():
        parts.append(CLAUDE_PATH.read_text(encoding="utf-8"))
    else:
        parts.append(
            "You are an autonomous options trading AI agent for Haim (חיים). "
            "Always respond in Hebrew. Financial terms stay in English."
        )

    if MEMORY_PATH.exists():
        parts.append("\n\n---\n\n## FULL MEMORY\n\n")
        parts.append(MEMORY_PATH.read_text(encoding="utf-8"))

    parts.append("""

---

## HOW TO BEHAVE IN CONVERSATION

You are Haim's personal trading AI. Talk naturally like Claude or ChatGPT — not like a bot.

PERSONALITY:
- Direct, analytical, warm when needed
- Proactively share insights without being asked
- If you notice something important in the data, mention it
- Use dry humor occasionally — Haim appreciates it

LANGUAGE:
- Always respond in Hebrew
- Keep financial/technical terms in English: IV, Delta, Strike, DTE, Call, Put, etc.
- Use bullet points for lists, but write naturally for explanations
- Keep Telegram-friendly formatting (avoid long walls of text)

WHEN ASKED ABOUT A STOCK:
You receive pre-fetched data in [Context data]. Use ALL of it:
- IV data: state IV Rank, Expected Move, liquidity
- Yahoo Finance: CHECK EARNINGS DATE FIRST — if earnings < 14 days → warn immediately
- Technical: state RSI, trend, support/resistance
- News: mention if relevant to trade decision
- Then recommend strategy based on IV Rank + technical context

EARNINGS WARNING RULE (non-negotiable):
If earnings are within 14 days → always say this first:
"⚠️ יש Earnings בעוד X ימים — שקול להמתין או להשתמש באסטרטגיית Earnings בלבד"

WHEN ASKED ABOUT POSITIONS:
- Read the [Context data] section — open positions are already listed there
- Calculate: current profit/loss, DTE remaining, alert if near management thresholds

WHEN ASKED ABOUT THE MARKET TODAY:
- Read the [Context data] section — the regime report is already there
- Summarize: verdict, VIX, SPY trend, key macro factors

WHEN ASKED FOR TRADE IDEAS:
- Read the [Context data] section — latest Agent 2 recommendations are already there
- Present the top ideas with full details

WHEN ASKED GENERAL OPTIONS QUESTIONS:
- Answer from your deep knowledge in MEMORY.md
- Give concrete examples with numbers, not just theory

NEVER:
- Give generic answers when specific data is available in [Context data]
- Recommend Naked options without warning about unlimited risk
- Recommend any trade without first checking IV Rank

---

IMPORTANT — HOW YOU GET DATA:
All real-time data is automatically fetched FOR YOU before you respond.
It appears in the [Context data available to you] section of the message.
You NEVER need to call tools or mention fetching data.
Just READ the context and answer naturally in Hebrew.
Never say "let me search" or "I'm fetching" — the data is already there.
Never mention tool names or APIs in your response.

---

CRITICAL FORMATTING RULES:
- NEVER output XML tags like <usemcptool>, <servername>, <arguments> etc.
- NEVER show internal tool calls or raw data structures to the user
- Always respond in clean, formatted Hebrew text only
- If data was fetched for you in [Context data], use it directly — do not reference tools
- Format responses with emojis and bullet points, never with XML or JSON
""")

    return "".join(parts)


# ── Data Fetchers ─────────────────────────────────────────────────────────────

def _extract_tickers(text: str) -> list[str]:
    """Extract ALL stock tickers from user message."""
    found = []
    # Match $TICKER or standalone UPPERCASE words
    for pattern in [r'\$([A-Z]{1,5})\b', r'\b([A-Z]{2,5})\b']:
        for m in re.findall(pattern, text.upper()):
            if m not in _SKIP_WORDS and 2 <= len(m) <= 5 and m not in found:
                found.append(m)
    return found[:5]  # max 5 tickers per message


def _fetch_stock_data(ticker: str) -> str:
    """Fetch comprehensive real-time data for a stock ticker."""
    results = []

    # 1. Real IV data from yfinance
    try:
        from app.services.realtime_market_data import get_realtime_iv_data
        iv = get_realtime_iv_data(ticker)
        if iv.current_price > 0:
            iv_signal = (
                "🔥 גבוה" if iv.iv_rank >= 50
                else ("✅ בינוני-גבוה" if iv.iv_rank >= 35
                      else ("⚠️ בינוני" if iv.iv_rank >= 20 else "❌ נמוך"))
            )
            if iv.iv_rank >= 50:
                strategy = "מכור פרמיה → Iron Condor / Bull Put Spread"
            elif iv.iv_rank >= 35:
                strategy = "Credit Spreads מוגדרי סיכון"
            elif iv.iv_rank >= 25:
                strategy = "Bull Put Spread בזהירות"
            else:
                strategy = "IV נמוך מדי לאסטרטגיות מכירה → שקול Debit Spread או LEAPs"

            results.append(
                f"[נתוני שוק אמיתיים — {ticker}]\n"
                f"מחיר: ${iv.current_price}\n"
                f"IV נוכחי: {iv.iv_current}%\n"
                f"IV Rank: {iv.iv_rank}/100 {iv_signal}\n"
                f"IV Percentile: {iv.iv_percentile}/100\n"
                f"Expected Move 30 יום: ±${iv.expected_move_30d}\n"
                f"ATM IV (Call/Put): {iv.atm_call_iv}% / {iv.atm_put_iv}%\n"
                f"Bid-Ask Spread: {iv.bid_ask_spread_pct}% ({'נזיל ✅' if iv.is_liquid else 'לא נזיל ⚠️'})\n"
                f"אסטרטגיה מומלצת: {strategy}\n"
                f"מקור: {iv.data_source}"
            )
    except Exception as e:
        logger.debug("IV fetch failed for %s: %s", ticker, e)

    # 2. XGBoost confidence
    try:
        from app.services.ml_service import predict_confidence
        conf = predict_confidence(ticker)
        if conf is not None:
            results.append(f"XGBoost Confidence: {conf:.1f}% (הסתברות לעלייה ≥5% ב-10 ימים)")
    except Exception:
        pass

    # 3. MongoDB sentiment for this ticker
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        cutoff = datetime.utcnow() - timedelta(hours=48)
        sent = db["daily_market_sentiment"].find_one(
            {"ticker": ticker, "timestamp": {"$gte": cutoff}},
            sort=[("timestamp", -1)],
        )
        if sent:
            score = sent.get("sentiment_score", 5)
            label = "שורי 📈" if score >= 7 else ("דובי 📉" if score <= 3 else "ניטרלי ➡️")
            results.append(f"סנטימנט AI: {score}/10 — {label}")
    except Exception:
        pass

    # 4. Yahoo Finance enrichment (earnings, news, stats)
    yahoo_data = _fetch_yahoo_enrichment(ticker)
    if yahoo_data:
        results.append(yahoo_data)

    # 5. Technical analysis (RSI, trend, support/resistance)
    tech = _fetch_technical_analysis(ticker)
    if tech:
        results.append(tech)

    return "\n\n".join(results) if results else ""


def _fetch_yahoo_enrichment(ticker: str) -> str:
    """
    Fetch earnings dates, recent news, and key stats from yfinance.
    This is the 'game changer' data that prevents trading into earnings.
    """
    try:
        import yfinance as yf
        from datetime import date as _date

        stock = yf.Ticker(ticker)
        lines = [f"[Yahoo Finance — {ticker}]"]

        # 1. Earnings date (CRITICAL)
        try:
            cal = stock.calendar
            if cal is not None and not cal.empty:
                if "Earnings Date" in cal.index:
                    earn_dates = cal.loc["Earnings Date"]
                    if hasattr(earn_dates, "iloc"):
                        earn_date = earn_dates.iloc[0]
                    else:
                        earn_date = earn_dates
                    if hasattr(earn_date, "date"):
                        earn_date = earn_date.date()
                    days_until = (earn_date - _date.today()).days
                    if 0 <= days_until <= 45:
                        warn = "⚠️ DANGER" if days_until <= 7 else ("⚠️ זהירות" if days_until <= 14 else "📅")
                        lines.append(f"Earnings: {earn_date} ({days_until} ימים) {warn}")
                        if days_until <= 7:
                            lines.append("❌ אל תמכור אופציות לפני Earnings — IV crush / gap risk!")
                    else:
                        lines.append(f"Earnings: {earn_date} ({days_until} ימים) ✅ בטוח")
        except Exception:
            pass

        # 2. Key stats
        try:
            info = stock.info
            pe = info.get("trailingPE")
            market_cap = info.get("marketCap", 0)
            sector = info.get("sector", "")
            short_pct = info.get("shortPercentOfFloat", 0)

            if market_cap:
                cap_str = f"${market_cap/1e9:.1f}B" if market_cap > 1e9 else f"${market_cap/1e6:.0f}M"
                lines.append(f"Market Cap: {cap_str} | Sector: {sector}")
            if pe:
                lines.append(f"P/E: {pe:.1f}")
            if short_pct and short_pct > 0.10:
                lines.append(f"⚠️ Short Interest: {short_pct*100:.1f}% (גבוה)")
        except Exception:
            pass

        # 3. Recent news headlines (last 3)
        try:
            news = stock.news
            if news:
                lines.append("📰 חדשות אחרונות:")
                for item in news[:3]:
                    title = item.get("title", "")
                    if title:
                        lines.append(f"  • {title[:80]}")
        except Exception:
            pass

        # 4. 52-week range
        try:
            info = stock.info
            low52 = info.get("fiftyTwoWeekLow")
            high52 = info.get("fiftyTwoWeekHigh")
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if low52 and high52 and price:
                pct_from_low = (price - low52) / (high52 - low52) * 100
                lines.append(f"52W: ${low52:.2f} — ${high52:.2f} | עכשיו: {pct_from_low:.0f}% מהשפל")
        except Exception:
            pass

        return "\n".join(lines) if len(lines) > 1 else ""

    except Exception as e:
        logger.debug("Yahoo enrichment failed for %s: %s", ticker, e)
        return ""


def _fetch_technical_analysis(ticker: str) -> str:
    """
    Calculate RSI, trend, support/resistance from yfinance price history.
    No TradingView API needed — pure yfinance.
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty or len(hist) < 20:
            return ""

        closes = hist["Close"]
        volumes = hist["Volume"]

        # RSI (14-day)
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = round(float(100 - (100 / (1 + rs.iloc[-1]))), 1)
        rsi_label = "⚠️ Overbought" if rsi > 70 else ("⚠️ Oversold" if rsi < 30 else "✅ Normal")

        # Trend (20 vs 50 MA)
        ma20 = float(closes.rolling(20).mean().iloc[-1])
        ma50 = float(closes.rolling(50).mean().iloc[-1])
        current = float(closes.iloc[-1])
        trend = "🟢 שורי" if ma20 > ma50 else "🔴 דובי"

        # Support & Resistance (20-day low/high)
        support = round(float(closes.rolling(20).min().iloc[-1]), 2)
        resistance = round(float(closes.rolling(20).max().iloc[-1]), 2)

        # Volume trend
        avg_vol = float(volumes.rolling(10).mean().iloc[-1])
        last_vol = float(volumes.iloc[-1])
        vol_note = "📈 Volume גבוה" if last_vol > avg_vol * 1.5 else ""

        return (
            f"[ניתוח טכני — {ticker}]\n"
            f"RSI(14): {rsi} {rsi_label}\n"
            f"Trend: {trend} (MA20: ${ma20:.2f} | MA50: ${ma50:.2f})\n"
            f"Support: ${support} | Resistance: ${resistance}\n"
            f"מחיר נוכחי: ${current:.2f} "
            f"({'קרוב ל-Resistance ⚠️' if current > resistance*0.97 else 'בטווח בטוח ✅'})"
            f"{' | ' + vol_note if vol_note else ''}"
        )
    except Exception as e:
        logger.debug("Technical analysis failed for %s: %s", ticker, e)
        return ""


def _fetch_open_positions() -> str:
    """Fetch all open positions from MongoDB."""
    try:
        from app.data.mongo_client import MongoDB
        from datetime import date
        db = MongoDB.get_db()
        positions = list(db["open_positions"].find(
            {"status": {"$nin": ["closed"]}},
            sort=[("opened_at", -1)],
        ))
        if not positions:
            return "[פוזיציות פתוחות: אין כרגע]"

        lines = [f"[פוזיציות פתוחות ({len(positions)})]"]
        for p in positions:
            exp = p.get("expiration_date", "")
            try:
                dte = (date.fromisoformat(exp) - date.today()).days
            except Exception:
                dte = "?"
            credit = float(p.get("credit_received", 0))
            lines.append(
                f"• {p['ticker']} — {p['strategy']}\n"
                f"  Strike: ${p.get('short_strike')} | Credit: ${credit} | "
                f"Exp: {exp} ({dte} DTE) | Status: {p.get('status')}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.debug("Positions fetch failed: %s", e)
        return ""


def _fetch_latest_regime() -> str:
    """Fetch the latest Agent 1 regime report."""
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        doc = db["market_regime_reports"].find_one(sort=[("timestamp", -1)])
        if not doc:
            return "[Regime: אין דוח עדיין — הרץ /regime]"
        verdict = doc.get("verdict", "?")
        vix = doc.get("vix", "?")
        trend = doc.get("spy_trend", "?")
        iv_rank = doc.get("iv_rank", "?")
        ts = doc.get("timestamp", "")[:16].replace("T", " ")
        emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(verdict, "⚪")
        return (
            f"[Regime Report — {ts}]\n"
            f"{emoji} ורדיקט: {verdict} | VIX: {vix} | "
            f"SPY: {trend} | IV Rank: {iv_rank}%"
        )
    except Exception:
        return ""


def _fetch_latest_trade_ideas() -> str:
    """Fetch today's trade ideas from Agent 2."""
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        doc = db["options_strategist_reports"].find_one(sort=[("timestamp", -1)])
        if not doc:
            return "[עסקאות: אין המלצות עדיין — הרץ /strategist]"
        ideas = doc.get("trade_ideas", [])
        if not ideas:
            return "[עסקאות: לא נמצאו הזדמנויות היום]"
        ts = doc.get("timestamp", "")[:16].replace("T", " ")
        lines = [f"[המלצות אחרונות — {ts}]"]
        for i, idea in enumerate(ideas[:3], 1):
            lines.append(
                f"{i}. {idea.get('ticker')} — {idea.get('strategy')} | "
                f"Strike: ${idea.get('short_strike')} | "
                f"Credit: ${idea.get('credit')} | "
                f"P(OTM): {idea.get('probability_otm')}%"
            )
        return "\n".join(lines)
    except Exception:
        return ""


def _get_iv_summary(ticker: str) -> str:
    """Get a one-line IV summary for a ticker."""
    try:
        from app.services.realtime_market_data import get_realtime_iv_data
        d = get_realtime_iv_data(ticker)
        if d.current_price <= 0:
            return "— אין נתונים"
        iv_emoji = "🔥" if d.iv_rank >= 50 else ("✅" if d.iv_rank >= 30 else "❄️")
        strategy = "מכור פרמיה" if d.iv_rank >= 50 else ("Spread" if d.iv_rank >= 30 else "LEAPs")
        return (f"| ${d.current_price} | IV Rank: {d.iv_rank:.0f}% {iv_emoji} "
                f"| EM: ±${d.expected_move_30d} | → {strategy}")
    except Exception:
        return "— אין נתונים"


def _fetch_finviz_candidates() -> str:
    """Fetch Finviz candidates AND their IV data."""
    try:
        from app.services.finviz_service import FinvizService
        bullish = FinvizService.get_bullish_tickers(n=5)
        bearish = FinvizService.get_bearish_tickers(n=5)

        lines = []

        if bullish:
            lines.append("📈 *Finviz שוריות + IV:*")
            for ticker in bullish[:5]:
                iv_str = _get_iv_summary(ticker)
                lines.append(f"• {ticker} {iv_str}")

        if bearish:
            lines.append("\n📉 *Finviz דוביות + IV:*")
            for ticker in bearish[:5]:
                iv_str = _get_iv_summary(ticker)
                lines.append(f"• {ticker} {iv_str}")

        return "\n".join(lines) if lines else ""
    except Exception as e:
        logger.debug("Finviz fetch failed: %s", e)
        return ""


def _fetch_market_sentiment() -> str:
    """Fetch average market sentiment from MongoDB."""
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        cutoff = datetime.utcnow() - timedelta(hours=24)
        docs = list(db["daily_market_sentiment"].find(
            {"timestamp": {"$gte": cutoff}},
            {"sentiment_score": 1, "ticker": 1},
        ))
        if not docs:
            return ""
        scores = [d["sentiment_score"] for d in docs if "sentiment_score" in d]
        if not scores:
            return ""
        avg = sum(scores) / len(scores)
        label = "שורי 📈" if avg >= 6.5 else ("דובי 📉" if avg <= 4 else "ניטרלי ➡️")
        top = sorted(docs, key=lambda x: x.get("sentiment_score", 5), reverse=True)[:3]
        top_tickers = [d.get("ticker", "?") for d in top]
        return (
            f"[סנטימנט שוק — 24 שעות אחרונות]\n"
            f"ממוצע: {avg:.1f}/10 — {label}\n"
            f"מניות עם סנטימנט גבוה: {', '.join(top_tickers)}"
        )
    except Exception:
        return ""


def _fetch_macro_calendar() -> str:
    """
    Fetch today's economic calendar and earnings via Perplexity.
    Called automatically when user asks market/macro questions.
    """
    try:
        from app.services.perplexity_service import PerplexityService
        from datetime import date as _date
        svc = PerplexityService()
        if not svc.is_available():
            return ""

        today = _date.today().strftime("%B %d, %Y")
        query = (
            f"Economic calendar for {today}: "
            f"1) Any FOMC Fed meetings or Fed speeches today or this week? "
            f"2) CPI, PPI, NFP, or other major economic data releases? "
            f"3) Major S&P 500 earnings reports this week? "
            f"Answer in 3 bullet points, be specific with dates and times."
        )
        answer = svc.ask(query)
        if answer:
            return f"[לוח אירועים מקרו — {today}]\n{answer}"
        return ""
    except Exception:
        return ""


def _fetch_perplexity(question: str) -> str:
    """Fetch real-time answer from Perplexity."""
    try:
        from app.services.perplexity_service import PerplexityService
        svc = PerplexityService()
        if svc.is_available():
            answer = svc.ask(question)
            if answer:
                return f"[Perplexity — נתונים בזמן אמת]\n{answer}"
    except Exception:
        pass
    return ""


def _fetch_openai_fact(question: str) -> str:
    """Fetch quick fact from OpenAI as fallback."""
    try:
        from app.services.openai_sentiment import get_quick_fact
        answer = get_quick_fact(question)
        if answer:
            return f"[OpenAI]\n{answer}"
    except Exception:
        pass
    return ""


# ── Intent Detection ──────────────────────────────────────────────────────────

def _detect_intent(text: str) -> list[str]:
    """Detect what data the user needs. Returns list of intent tags."""
    text_lower = text.lower()
    intents = []

    stock_keywords = ['iv', 'אופציה', 'מניה', 'מחיר', 'spread', 'strike',
                      'delta', 'condor', 'put', 'call', 'עסקה', 'טרייד',
                      'נסרוק', 'בדוק', 'תבדוק', 'analyze', 'ניתוח']
    if any(k in text_lower for k in stock_keywords):
        intents.append("stock_data")

    position_keywords = ['פוזיציה', 'פוזיציות', 'position', 'פתוח', 'open',
                         'הפסד', 'רווח', 'portfolio']
    if any(k in text_lower for k in position_keywords):
        intents.append("positions")

    regime_keywords = ['שוק', 'regime', 'vix', 'spy', 'היום', 'מצב', 'ורדיקט',
                       'לסחור', 'market', 'trend']
    if any(k in text_lower for k in regime_keywords):
        intents.append("regime")

    ideas_keywords = ['המלצה', 'רעיון', 'idea', 'מה לקנות', 'מה למכור',
                      'הזדמנות', 'opportunity', 'strategist']
    if any(k in text_lower for k in ideas_keywords):
        intents.append("ideas")

    sentiment_keywords = ['סנטימנט', 'sentiment', 'שורי', 'דובי', 'bullish', 'bearish']
    if any(k in text_lower for k in sentiment_keywords):
        intents.append("sentiment")

    scan_keywords = ['סריקה', 'scan', 'finviz', 'מועמדים', 'candidates',
                     'רשימה', 'מניות', 'חפש', 'מצא', 'stocks', 'screener',
                     'high iv', 'iv rank']
    if any(k in text_lower for k in scan_keywords):
        intents.append("scan")

    realtime_keywords = ['היום', 'עכשיו', 'חדשות', 'news', 'פד', 'fed',
                         'אמר', 'הודיע', 'earnings', 'דוחות', 'breaking',
                         'finviz', 'בחוץ', 'מהאינטרנט', 'חפש באינטרנט', 'search']
    if any(k in text_lower for k in realtime_keywords):
        intents.append("realtime")

    # 0DTE specific
    zero_dte_keywords = ['0dte', '0 dte', 'אפס', 'intraday', 'straddle',
                         'gamma', 'גאמא', 'scalp', 'zero dte']
    if any(k in text_lower for k in zero_dte_keywords):
        intents.append("zero_dte")

    return intents


# ── Context Builder ───────────────────────────────────────────────────────────

async def _build_context(text: str) -> str:
    """Build all relevant context based on detected intents."""
    intents = _detect_intent(text)
    context_parts = []

    # Auto-fetch real IV data for ALL tickers mentioned
    tickers = _extract_tickers(text)
    for ticker in tickers:
        stock_ctx = _fetch_stock_data(ticker)
        if stock_ctx:
            context_parts.append(stock_ctx)

    # Always add regime if market-related
    regime = _fetch_latest_regime()
    if regime:
        context_parts.append(regime)

    if "positions" in intents:
        pos = _fetch_open_positions()
        if pos:
            context_parts.append(pos)

    if "ideas" in intents:
        ideas = _fetch_latest_trade_ideas()
        if ideas:
            context_parts.append(ideas)

    if "sentiment" in intents:
        sent = _fetch_market_sentiment()
        if sent:
            context_parts.append(sent)

    if "finviz" in intents or "scan" in intents:
        fvz = _fetch_finviz_candidates()
        if fvz:
            context_parts.append(fvz)
        # Also fetch market sentiment when scanning
        sent = _fetch_market_sentiment()
        if sent:
            context_parts.append(sent)

    if "regime" in intents or "realtime" in intents:
        macro = _fetch_macro_calendar()
        if macro:
            context_parts.append(macro)

    if "realtime" in intents:
        pplx = _fetch_perplexity(text)
        if pplx:
            context_parts.append(pplx)
        else:
            oai = _fetch_openai_fact(text)
            if oai:
                context_parts.append(oai)

    if "zero_dte" in intents:
        try:
            from app.services.zero_dte_scanner import analyze_zero_dte, format_zero_dte_report
            for sym in ["SPY", "QQQ"]:
                setup = analyze_zero_dte(sym)
                if setup:
                    context_parts.append(format_zero_dte_report(setup))
        except Exception:
            pass

    return "\n\n---\n\n".join(context_parts) if context_parts else ""


# ── Conversation Memory ───────────────────────────────────────────────────────

class ConversationMemory:
    def __init__(self):
        self._histories: dict[int, deque] = {}

    def get(self, user_id: int) -> list[dict]:
        return list(self._histories.get(user_id, deque(maxlen=MAX_HISTORY)))

    def add(self, user_id: int, role: str, content: str):
        if user_id not in self._histories:
            self._histories[user_id] = deque(maxlen=MAX_HISTORY)
        self._histories[user_id].append({"role": role, "content": content})

    def reset(self, user_id: int):
        self._histories.pop(user_id, None)


# ── Main Handler ──────────────────────────────────────────────────────────────

class FreeChatHandler:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._memory = ConversationMemory()
        self._system_prompt = _build_system_prompt()
        logger.info("FreeChatHandler initialized (model=%s)", CLAUDE_MODEL)

    def reload_memory(self):
        self._system_prompt = _build_system_prompt()
        logger.info("System prompt reloaded")

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        text = update.message.text.strip()

        if text.lower() == "/reset":
            self._memory.reset(user_id)
            await update.message.reply_text("🔄 שיחה אופסה. נתחיל מחדש, חיים.")
            return

        if text.lower().startswith("/learn"):
            await self._handle_learn(update, text)
            return

        await self._handle_chat(update, user_id, text)

    async def _handle_chat(self, update: Update, user_id: int, text: str) -> None:
        """Main chat handler — feels like Claude/ChatGPT."""
        await update.message.chat.send_action(ChatAction.TYPING)

        context_data = await _build_context(text)

        user_content = text
        if context_data:
            user_content = f"{text}\n\n[Context data available to you]:\n{context_data}"

        self._memory.add(user_id, "user", user_content)

        try:
            response = self._client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                system=self._system_prompt,
                messages=self._memory.get(user_id),
            )
            reply = response.content[0].text
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            reply = "⚠️ שגיאה זמנית בחיבור ל-AI. נסה שוב בעוד רגע."

        self._memory.add(user_id, "assistant", reply)

        for chunk in _split_message(reply):
            await update.message.reply_text(chunk, parse_mode="Markdown")

    async def _handle_learn(self, update: Update, text: str) -> None:
        """Append new knowledge to MEMORY.md."""
        content = text[len("/learn"):].strip()

        if not content:
            await update.message.reply_text(
                "📚 *שימוש:* `/learn <טקסט>`\n\nהדבק כל מידע שאתה רוצה שאלמד.",
                parse_mode="Markdown",
            )
            return

        if re.match(r"https?://", content):
            await update.message.reply_text(
                "🔗 זיהיתי קישור. תעתיק את הטקסט מהדף והדבק אותו עם /learn."
            )
            return

        await update.message.chat.send_action(ChatAction.TYPING)
        try:
            resp = self._client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=(
                    "Extract trading insights from the following text. "
                    "Return dense bullet points capturing key rules, facts, or strategies. "
                    "Financial terms in English, explanation in Hebrew."
                ),
                messages=[{"role": "user", "content": content}],
            )
            summary = resp.content[0].text
        except Exception:
            summary = content

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n\n---\n\n## 📚 נלמד ב-{timestamp}\n\n{summary}\n"

        try:
            with open(MEMORY_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
            self.reload_memory()
            await update.message.reply_text(
                f"✅ *למדתי ושמרתי!*\n\n{summary[:500]}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("MEMORY.md write failed: %s", e)
            await update.message.reply_text("⚠️ שגיאה בשמירה לזיכרון.")


# ── Helper ────────────────────────────────────────────────────────────────────

def _split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current, current_len = [], [], 0
    for para in text.split("\n\n"):
        if current_len + len(para) + 2 > limit:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks
