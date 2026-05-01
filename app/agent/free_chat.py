"""
free_chat.py — Real Conversational AI Agent
============================================

Real AI agent that:
1. Remembers all previous conversations (MongoDB)
2. Knows who Haim is (profile)
3. Searches the internet for every relevant question
4. Can read URLs, images, and documents
5. Learns and improves over time

Architecture:
User message → Extract tickers/intent → Fetch live data →
Build context (history + profile + market data + internet) →
Claude responds → Save to memory → Send to Telegram
"""

import asyncio
import base64
import logging
import os
import re
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-6"
MAX_TOKENS        = 1500

_ROOT       = Path(__file__).parent.parent.parent
MEMORY_PATH = _ROOT / "MEMORY.md"
CLAUDE_PATH = _ROOT / "CLAUDE.md"

# Words to skip when extracting tickers
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


class TradingAgent:
    """
    The main AI trading agent.
    Combines persistent memory, internet, market data, and Claude.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.memory = self._init_memory()

    def _init_memory(self):
        try:
            from app.services.memory_engine import MemoryEngine
            return MemoryEngine()
        except Exception as e:
            logger.warning("Memory engine unavailable: %s", e)
            return None

    # ── Ticker & Intent Detection ────────────────────────────────────────────

    def _extract_tickers(self, text: str) -> list[str]:
        found = []
        for pattern in [r'\$([A-Z]{1,5})\b', r'\b([A-Z]{2,5})\b']:
            for m in re.findall(pattern, text.upper()):
                if m not in _SKIP_WORDS and 2 <= len(m) <= 5 and m not in found:
                    found.append(m)
        return found[:5]

    def _detect_intent(self, text: str) -> list[str]:
        text_lower = text.lower()
        intents = []

        if any(w in text_lower for w in ["שוק", "ריג'ים", "regime", "vix", "spy", "מאקרו", "היום", "market"]):
            intents.append("market")
        if any(w in text_lower for w in ["אסטרטגיה", "strategy", "spread", "condor", "put", "call", "straddle"]):
            intents.append("strategy")
        if any(w in text_lower for w in ["מחיר", "price", "iv", "רנק", "rank", "ניתוח", "analyze"]):
            intents.append("analysis")
        if any(w in text_lower for w in ["חדשות", "news", "earnings", "דוחות", "הכריז", "הודיע"]):
            intents.append("news")
        if any(w in text_lower for w in ["תלמד", "learn", "http", "www", "קישור", "pdf"]):
            intents.append("learn")
        if any(w in text_lower for w in ["פוזיציה", "position", "הפסד", "רווח", "pnl", "portfolio"]):
            intents.append("positions")
        if any(w in text_lower for w in ["0dte", "אפס", "intraday", "היום בלבד", "gamma", "גאמא"]):
            intents.append("zero_dte")
        if any(w in text_lower for w in ["סריקה", "scan", "finviz", "מועמדים", "candidates", "high iv"]):
            intents.append("scan")
        if any(w in text_lower for w in ["סנטימנט", "sentiment", "שורי", "דובי", "bullish", "bearish"]):
            intents.append("sentiment")

        return intents if intents else ["general"]

    # ── Data Fetching ────────────────────────────────────────────────────────

    def _fetch_market_data(self, ticker: str) -> str:
        """Fetch comprehensive market data for a ticker."""
        results = []

        # Live price from WebSocket cache
        try:
            from app.services.realtime_stream import get_live_price, format_live_price_note
            live = get_live_price(ticker)
            if live:
                results.append(f"[מחיר חי — {ticker}]\n{format_live_price_note(ticker, live)}")
        except Exception:
            pass

        # Deep smart scan (fundamentals + momentum + Perplexity)
        try:
            from app.services.smart_scanner import deep_scan_ticker, format_smart_scan_hebrew
            smart = deep_scan_ticker(ticker, fetch_perplexity=True)
            if smart:
                results.append(format_smart_scan_hebrew(smart))
                try:
                    from app.services.tradingview_service import enrich_ticker_context
                    tv_ctx = enrich_ticker_context(ticker)
                    if tv_ctx:
                        results.append(tv_ctx)
                except Exception:
                    pass
                return "\n\n".join(results)
        except Exception:
            pass

        # Fallback: Real IV data
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
                    strategy = "IV נמוך → שקול Debit Spread או LEAPs"
                results.append(
                    f"[נתוני שוק — {ticker}]\n"
                    f"מחיר: ${iv.current_price} | IV: {iv.iv_current}%\n"
                    f"IV Rank: {iv.iv_rank}/100 {iv_signal}\n"
                    f"Expected Move 30d: ±${iv.expected_move_30d}\n"
                    f"אסטרטגיה: {strategy}"
                )
        except Exception:
            pass

        # Technical analysis
        try:
            from app.services.technical_indicators import get_technical_snapshot, format_technical_hebrew
            snap = get_technical_snapshot(ticker)
            if snap:
                results.append(format_technical_hebrew(snap))
        except Exception:
            pass

        # Yahoo Finance (earnings, stats, news)
        try:
            import yfinance as yf
            from datetime import date as _date
            stock = yf.Ticker(ticker)
            lines = [f"[Yahoo Finance — {ticker}]"]
            try:
                cal = stock.calendar
                if cal is not None and not cal.empty and "Earnings Date" in cal.index:
                    earn = cal.loc["Earnings Date"]
                    if hasattr(earn, "iloc"):
                        earn = earn.iloc[0]
                    if hasattr(earn, "date"):
                        earn = earn.date()
                    days = (earn - _date.today()).days
                    if 0 <= days <= 45:
                        warn = "⚠️ DANGER" if days <= 7 else ("⚠️" if days <= 14 else "📅")
                        lines.append(f"Earnings: {earn} ({days} ימים) {warn}")
                        if days <= 7:
                            lines.append("❌ אל תמכור אופציות לפני Earnings!")
            except Exception:
                pass
            if len(lines) > 1:
                results.append("\n".join(lines))
        except Exception:
            pass

        # XGBoost confidence
        try:
            from app.services.ml_service import predict_confidence
            conf = predict_confidence(ticker)
            if conf is not None:
                results.append(f"XGBoost: {conf:.1f}% הסתברות לעלייה ≥5% ב-10 ימים")
        except Exception:
            pass

        return "\n\n".join(results)

    def _fetch_internet(self, query: str, ticker: str = "") -> str:
        """Search the internet via Perplexity."""
        try:
            from app.services.perplexity_service import PerplexityService
            svc = PerplexityService()
            if not svc.is_available():
                return ""
            if ticker:
                return svc.get_stock_news(ticker) or ""
            return svc.ask(query) or ""
        except Exception as e:
            logger.debug("Perplexity failed: %s", e)
        return ""

    def _fetch_market_regime(self) -> str:
        """Get current market regime from MongoDB."""
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            doc = db["market_regime_reports"].find_one(sort=[("timestamp", -1)])
            if doc:
                verdict = doc.get("verdict", "YELLOW")
                vix = doc.get("vix", 0)
                trend = doc.get("spy_trend", "?")
                emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(verdict, "⚪")
                ts = str(doc.get("timestamp", ""))[:16].replace("T", " ")
                return f"[Regime — {ts}]\n{emoji} {verdict} | VIX: {vix} | SPY: {trend}"
        except Exception:
            pass
        return ""

    def _fetch_open_positions(self) -> str:
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
                lines.append(
                    f"• {p['ticker']} — {p['strategy']}\n"
                    f"  Strike: ${p.get('short_strike')} | Credit: ${p.get('credit_received')} | "
                    f"Exp: {exp} ({dte} DTE)"
                )
            return "\n".join(lines)
        except Exception:
            return ""

    def _fetch_pcr_signal(self) -> str:
        try:
            from app.services.pcr_signal import get_pcr_signal, format_pcr_hebrew
            pcr = get_pcr_signal("SPY")
            return format_pcr_hebrew(pcr) if pcr else ""
        except Exception:
            return ""

    def _fetch_url_content(self, url: str) -> str:
        return self._fetch_internet(
            f"Summarize main content and key information at: {url}"
        )

    def _process_image(self, image_data: bytes, mime_type: str) -> list:
        b64 = base64.standard_b64encode(image_data).decode("utf-8")
        return [{"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}}]

    # ── Live Data Fetcher ────────────────────────────────────────────────────

    def _fetch_live_data_for_query(self, text: str, tickers: list[str]) -> str:
        """
        Intelligently fetch real-time data based on what the user asked.
        This is the core of the agent's ability to 'know' current data.
        """
        import yfinance as yf
        from datetime import date
        parts = []
        text_lower = text.lower()

        # ── 1. SPX/SPY current price ──────────────────────────────────────────
        if any(w in text_lower for w in ["spx", "spy", "s&p", "מדד", "איפה עומד"]):
            try:
                spy = yf.Ticker("SPY")
                hist = spy.history(period="2d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    change = (price / prev - 1) * 100
                    emoji = "📈" if change >= 0 else "📉"
                    parts.append(
                        f"[SPY/SPX עכשיו]\n"
                        f"{emoji} SPY: ${price:.2f} ({change:+.2f}%)\n"
                        f"SPX ≈ ${price * 10:.0f} (SPY × 10)"
                    )
            except Exception as e:
                parts.append(f"[SPY] שגיאה: {e}")

        # ── 2. Options Chain for specific tickers ─────────────────────────────
        if any(w in text_lower for w in [
            "strike", "options chain", "chain", "puts", "calls",
            "אופציות", "שביתה", "ספציפי"
        ]):
            symbols = tickers if tickers else ["SPY"]
            for symbol in symbols[:2]:
                try:
                    stock = yf.Ticker(symbol)
                    price = float(stock.history(period="1d")["Close"].iloc[-1])
                    expirations = stock.options

                    if not expirations:
                        continue

                    # Get nearest expiration with 25-45 DTE
                    today = date.today()
                    target_exp = None
                    for exp in expirations:
                        from datetime import date as d
                        exp_date = d.fromisoformat(exp)
                        dte = (exp_date - today).days
                        if 15 <= dte <= 50:
                            target_exp = exp
                            break

                    if not target_exp:
                        target_exp = expirations[0]

                    chain = stock.option_chain(target_exp)
                    exp_date = date.fromisoformat(target_exp)
                    dte = (exp_date - today).days

                    # Get ATM puts (for Bull Put Spread)
                    puts = chain.puts
                    puts_near = puts[
                        (puts["strike"] >= price * 0.85) &
                        (puts["strike"] <= price * 1.0) &
                        (puts["bid"] > 0.05)
                    ].sort_values("strike", ascending=False).head(6)

                    # Get ATM calls (for Bear Call Spread)
                    calls = chain.calls
                    calls_near = calls[
                        (calls["strike"] >= price * 1.0) &
                        (calls["strike"] <= price * 1.15) &
                        (calls["bid"] > 0.05)
                    ].sort_values("strike").head(6)

                    puts_text = "\n".join([
                        f"  Put ${row['strike']:.0f} | Bid: ${row['bid']:.2f} "
                        f"| Ask: ${row['ask']:.2f} "
                        f"| OI: {int(row.get('openInterest', 0) or 0):,}"
                        for _, row in puts_near.iterrows()
                    ])

                    calls_text = "\n".join([
                        f"  Call ${row['strike']:.0f} | Bid: ${row['bid']:.2f} "
                        f"| Ask: ${row['ask']:.2f} "
                        f"| OI: {int(row.get('openInterest', 0) or 0):,}"
                        for _, row in calls_near.iterrows()
                    ])

                    parts.append(
                        f"[Options Chain — {symbol}]\n"
                        f"מחיר: ${price:.2f} | פקיעה: {target_exp} ({dte} DTE)\n\n"
                        f"📉 Puts (לBull Put Spread):\n{puts_text}\n\n"
                        f"📈 Calls (לBear Call Spread):\n{calls_text}"
                    )

                except Exception as e:
                    parts.append(f"[Options Chain {symbol}] שגיאה: {e}")

        # ── 3. GDP / Economic data reaction ──────────────────────────────────
        if any(w in text_lower for w in [
            "gdp", 'תמ"ג', "nfp", "cpi", "jobs",
            "economic", "כלכלי", "אינפלציה", "תגובת השוק"
        ]):
            news = self._fetch_internet(
                f"What is the stock market reaction to the latest GDP or "
                f"economic data today {date.today().strftime('%B %d %Y')}? "
                f"SPY price change, sector reactions, Fed implications.",
            )
            if news:
                parts.append(f"[תגובת שוק לנתונים כלכליים]\n{news}")

        # ── 4. VIX current ───────────────────────────────────────────────────
        if any(w in text_lower for w in ["vix", "תנודתיות", "פחד"]):
            try:
                vix = yf.Ticker("^VIX")
                hist = vix.history(period="2d")
                if not hist.empty:
                    v = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    chg = (v / prev - 1) * 100
                    regime = (
                        "🟢 שוק רגוע" if v < 15 else
                        "✅ נורמלי" if v < 20 else
                        "⚠️ מוגבר" if v < 25 else
                        "🔴 גבוה"
                    )
                    parts.append(
                        f"[VIX עכשיו]\n"
                        f"VIX: {v:.2f} ({chg:+.1f}%) — {regime}"
                    )
            except Exception:
                pass

        # ── 5. Specific ticker price + basic info ────────────────────────────
        for ticker in tickers[:3]:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d")
                if hist.empty:
                    continue
                price = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = (price / prev - 1) * 100
                emoji = "📈" if chg >= 0 else "📉"

                vol = int(hist["Volume"].iloc[-1])
                avg_vol = int(hist["Volume"].mean())
                vol_ratio = vol / avg_vol if avg_vol > 0 else 1

                parts.append(
                    f"[{ticker} — נתון חי]\n"
                    f"{emoji} מחיר: ${price:.2f} ({chg:+.2f}%)\n"
                    f"Volume: {vol:,} ({vol_ratio:.1f}x ממוצע)"
                )
            except Exception:
                pass

        # ── 6. General news search if nothing specific found ─────────────────
        if not parts and (tickers or len(text) > 20):
            query = text[:200]
            if tickers:
                query = f"{' '.join(tickers)} — {text[:150]}"
            news = self._fetch_internet(query)
            if news:
                parts.append(f"[נתוני אינטרנט]\n{news}")

        # ── 7. SPY + VIX baseline — always included ───────────────────────────
        if not any("SPY" in p or "VIX" in p for p in parts):
            try:
                spy_hist = yf.Ticker("SPY").history(period="2d")
                vix_hist = yf.Ticker("^VIX").history(period="2d")
                if not spy_hist.empty and not vix_hist.empty:
                    spy_price = float(spy_hist["Close"].iloc[-1])
                    spy_prev = float(spy_hist["Close"].iloc[-2])
                    spy_chg = (spy_price / spy_prev - 1) * 100
                    vix_price = float(vix_hist["Close"].iloc[-1])
                    parts.append(
                        f"[מצב שוק עכשיו]\n"
                        f"SPY: ${spy_price:.2f} ({spy_chg:+.1f}%) | "
                        f"VIX: {vix_price:.2f}"
                    )
            except Exception:
                pass

        return "\n\n".join(parts)

    # ── Context Builder ──────────────────────────────────────────────────────

    def _build_context(self, text: str, tickers: list[str], intents: list[str]) -> str:
        """Build rich context from market data + internet based on intent."""
        parts = []
        text_lower = text.lower()

        # ── LIVE DATA FETCH (most important — goes first) ─────────────────────
        live_data = self._fetch_live_data_for_query(text, tickers)
        if live_data:
            parts.insert(0, live_data)

        # Market regime (always useful)
        regime = self._fetch_market_regime()
        if regime:
            parts.append(regime)

        # TradingView market snapshot for market questions
        if any(w in text_lower for w in ["שוק", "spy", "vix", "market", "מאקרו", "snapshot"]):
            try:
                from app.services.tradingview_service import get_market_context_for_agent1
                tv = get_market_context_for_agent1()
                if tv:
                    parts.append(tv)
            except Exception:
                pass

        # Perplexity macro today
        if any(w in text_lower for w in ["שוק", "היום", "מאקרו", "fed", "vix", "market", "economy"]):
            try:
                from app.services.perplexity_service import PerplexityService
                svc = PerplexityService()
                macro = svc.get_macro_today()
                if macro:
                    parts.append(f"[אינטרנט — אירועי היום]\n{macro}")
            except Exception:
                pass

        # Stock-specific data
        for ticker in tickers[:3]:
            data = self._fetch_market_data(ticker)
            if data:
                parts.append(data)
            # Internet news for each ticker
            try:
                from app.services.perplexity_service import PerplexityService
                news = PerplexityService().get_stock_news(ticker)
                if news:
                    parts.append(f"[אינטרנט — חדשות {ticker}]\n{news}")
            except Exception:
                pass

        # PCR Signal
        if "sentiment" in intents or "market" in intents:
            pcr = self._fetch_pcr_signal()
            if pcr:
                parts.append(f"[PCR Signal]\n{pcr}")

        # Open positions
        if "positions" in intents:
            pos = self._fetch_open_positions()
            if pos:
                parts.append(pos)

        # 0DTE analysis
        if "zero_dte" in intents:
            try:
                from app.services.zero_dte_scanner import analyze_zero_dte, format_zero_dte_report
                for sym in ["SPY", "QQQ"]:
                    setup = analyze_zero_dte(sym)
                    if setup:
                        parts.append(format_zero_dte_report(setup))
            except Exception:
                pass

        # Finviz candidates
        if "scan" in intents:
            try:
                from app.services.finviz_service import FinvizService
                bullish = FinvizService.get_bullish_tickers(n=5)
                if bullish:
                    parts.append(f"[Finviz — שוריות]\n" + "\n".join(f"• {t}" for t in bullish))
            except Exception:
                pass

        # Relevant learned knowledge
        if self.memory:
            knowledge = self.memory.get_relevant_knowledge(text)
            for k in knowledge:
                parts.append(f"[ידע שנלמד — {k.get('topic', '')}]\n{k.get('content', '')[:500]}")

        # URL detection — learn or fetch for context
        urls = re.findall(r'https?://[^\s]+', text)
        learn_keywords = ["תלמד", "learn", "קרא", "read", "שמור", "save", "למד"]
        for url in urls[:2]:
            if any(w in text.lower() for w in learn_keywords):
                try:
                    from app.services.learning_engine import LearningEngine
                    result = LearningEngine().learn_from_url(url)
                    if result.get("success"):
                        parts.append(
                            f"[למדתי מהקישור: {url}]\n"
                            f"נושא: {result['topic']}\n"
                            f"{result['summary']}"
                        )
                except Exception:
                    pass
            else:
                content = self._fetch_url_content(url)
                if content:
                    parts.append(f"[תוכן מהקישור: {url}]\n{content[:1000]}")

        # Generic internet search fallback
        if not tickers and "general" not in intents and not urls:
            internet = self._fetch_internet(text[:200])
            if internet:
                parts.append(f"[אינטרנט]\n{internet}")

        # Always search internet when tickers are mentioned and live data didn't cover it
        if tickers and not live_data:
            for ticker in tickers[:2]:
                internet = self._fetch_internet(
                    f"Current {ticker} stock price, news, and options activity today",
                    ticker,
                )
                if internet:
                    parts.append(f"[{ticker} — אינטרנט]\n{internet}")

        return "\n\n---\n\n".join(parts)

    # ── Main Chat Handler ────────────────────────────────────────────────────

    async def handle_message(
        self,
        text: str,
        image_data: bytes = None,
        image_mime: str = None,
        document_text: str = None,
    ) -> str:
        """Main entry point for every user message."""
        if self.memory:
            self.memory.save_message("user", text)

        tickers = self._extract_tickers(text)
        intents = self._detect_intent(text)

        if self.memory and tickers:
            for t in tickers:
                self.memory.add_mentioned_ticker(t)

        # Build context in thread (blocking IO)
        context_data = await asyncio.to_thread(
            self._build_context, text, tickers, intents
        )

        # Dynamic system prompt (evolves with every conversation)
        if self.memory:
            system_prompt = self.memory.build_dynamic_system_prompt()
        else:
            system_prompt = _build_fallback_system_prompt()

        if context_data:
            system_prompt += f"\n\n═══ נתונים עדכניים ═══\n{context_data}"

        # Build conversation history (exclude current turn)
        history = []
        if self.memory:
            history = self.memory.get_messages_as_claude_format(limit=20)
            if history and history[-1]["role"] == "user":
                history = history[:-1]

        # Build user content
        user_content: list = []
        if image_data and image_mime:
            user_content.extend(self._process_image(image_data, image_mime))
        if document_text:
            user_content.append({"type": "text", "text": f"[מסמך מצורף]\n{document_text[:3000]}"})
        user_content.append({"type": "text", "text": text})

        messages = history + [{"role": "user", "content": user_content}]

        # Call Claude
        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=messages,
            )
            reply = response.content[0].text.strip()
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            reply = f"⚠️ שגיאה בתקשורת עם AI: {e}"

        if self.memory:
            self.memory.save_message("assistant", reply)
            # Self-improvement: learn from this conversation
            self.memory.learn_from_conversation(text, reply)

        return reply

    # ── Learning ─────────────────────────────────────────────────────────────

    async def learn_from_url(self, url: str) -> str:
        content = await asyncio.to_thread(self._fetch_url_content, url)
        if not content or len(content) < 50:
            return f"⚠️ לא הצלחתי לקרוא את הקישור: {url}"
        topic = url.split("/")[-1][:50] or url[:50]
        if self.memory:
            self.memory.save_knowledge(topic, content, source=url)
        return (
            f"✅ למדתי מהקישור!\n"
            f"נושא: {topic}\n"
            f"נשמר {len(content)} תווים לזיכרון."
        )

    async def learn_from_text(self, topic: str, content: str) -> str:
        if self.memory:
            self.memory.save_knowledge(topic, content, source="user")
        return f"✅ שמרתי את המידע!\nנושא: {topic}"

    # ── Legacy /learn ─────────────────────────────────────────────────────────

    async def handle_learn(self, text: str) -> str:
        """Append knowledge extracted by Claude to MongoDB and MEMORY.md."""
        content = text[len("/learn"):].strip()
        if not content:
            return "📚 *שימוש:* `/learn <טקסט>`"

        if re.match(r"https?://", content):
            return await self.learn_from_url(content)

        # Use Claude to extract insights
        try:
            resp = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=(
                    "Extract trading insights from the text. "
                    "Return dense bullet points: key rules, facts, strategies. "
                    "Financial terms in English, explanations in Hebrew."
                ),
                messages=[{"role": "user", "content": content}],
            )
            summary = resp.content[0].text
        except Exception:
            summary = content

        topic = f"learn_{datetime.now().strftime('%Y%m%d_%H%M')}"
        if self.memory:
            self.memory.save_knowledge(topic, summary, source="user")

        # Also append to MEMORY.md for backward compatibility
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n\n---\n\n## 📚 נלמד ב-{timestamp}\n\n{summary}\n"
            with open(MEMORY_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

        return f"✅ *למדתי ושמרתי!*\n\n{summary[:500]}"


# ── Fallback system prompt (no memory engine) ────────────────────────────────

def _build_fallback_system_prompt() -> str:
    parts = []
    if CLAUDE_PATH.exists():
        parts.append(CLAUDE_PATH.read_text(encoding="utf-8"))
    else:
        parts.append(
            "You are an autonomous options trading AI agent for Haim (חיים). "
            "Always respond in Hebrew. Financial terms stay in English."
        )
    if MEMORY_PATH.exists():
        parts.append(f"\n\n---\n\n## MEMORY\n\n{MEMORY_PATH.read_text(encoding='utf-8')}")
    return "".join(parts)


# ── Helper ────────────────────────────────────────────────────────────────────

def split_message(text: str, limit: int = 4000) -> list[str]:
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


# ── Singleton ─────────────────────────────────────────────────────────────────

_agent: Optional[TradingAgent] = None


def get_agent() -> TradingAgent:
    global _agent
    if _agent is None:
        _agent = TradingAgent()
    return _agent
