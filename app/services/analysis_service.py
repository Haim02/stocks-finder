"""
Deep Dive Analysis Service
==========================
Orchestrates multi-source data collection for a single ticker.
Called by the Telegram /analyze command.

Returns a rich dict consumed by:
  - AIService.get_deep_dive_analysis()   → Hebrew research note
  - EmailService.send_deep_dive_report() → HTML email
  - Telegram bot                         → short summary message
"""

import logging
from datetime import datetime

import pytz
import yfinance as yf

logger = logging.getLogger(__name__)


class AnalysisService:
    """Collect and merge all data needed for a Deep Dive report."""

    def analyze(self, ticker: str) -> dict:
        """
        Run full data collection for `ticker`.
        All sub-fetches are fault-tolerant — a failure in one source
        never blocks the others.
        """
        ticker = ticker.upper().strip()
        result: dict = {
            "ticker":    ticker,
            "timestamp": datetime.now(pytz.utc).isoformat(),
            # Technical defaults
            "rsi":             None,
            "sma50":           None,
            "sma200":          None,
            "macd":            None,
            "macd_signal":     None,
            "macd_histogram":  None,
            "week_52_low":     None,
            "week_52_high":    None,
            # News / history defaults
            "news":              [],
            "top_headline":      "No recent news",
            "sentiment_history": [],
            "recently_alerted":  False,
            "recently_options":  False,
        }

        self._fetch_fundamentals(ticker, result)
        self._fetch_technicals(ticker, result)
        self._fetch_news(ticker, result)
        self._fetch_mongo_history(ticker, result)

        logger.info(
            "[AnalysisService] %s — price=%s RSI=%s news=%d",
            ticker,
            result.get("current_price", "N/A"),
            result.get("rsi", "N/A"),
            len(result["news"]),
        )
        return result

    # ── Data fetchers ──────────────────────────────────────────────────────

    def _fetch_fundamentals(self, ticker: str, result: dict) -> None:
        """Fundamentals via FinancialAnalyzer (yfinance + api_hub institutional)."""
        try:
            from app.services.financial_service import FinancialAnalyzer
            data = FinancialAnalyzer().analyze(ticker)
            if data:
                result.update(data)
        except Exception:
            logger.debug("Fundamentals fetch failed for %s", ticker, exc_info=True)

    def _fetch_technicals(self, ticker: str, result: dict) -> None:
        """
        RSI(14), MACD(12/26/9), SMA50/200, 52-week range.
        Computed from yfinance OHLCV — no external API needed.
        """
        try:
            hist = yf.Ticker(ticker).history(period="1y")
            if len(hist) < 30:
                return

            close = hist["Close"]

            # ── RSI(14) ────────────────────────────────────────────────────
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rs    = gain / loss.replace(0, float("nan"))
            rsi   = 100 - (100 / (1 + rs))
            result["rsi"] = round(float(rsi.iloc[-1]), 1)

            # ── SMA 50 / 200 ───────────────────────────────────────────────
            if len(hist) >= 50:
                result["sma50"] = round(float(close.rolling(50).mean().iloc[-1]), 2)
            if len(hist) >= 200:
                result["sma200"] = round(float(close.rolling(200).mean().iloc[-1]), 2)

            # ── MACD (12/26/9) ─────────────────────────────────────────────
            ema12       = close.ewm(span=12, adjust=False).mean()
            ema26       = close.ewm(span=26, adjust=False).mean()
            macd_line   = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            result["macd"]           = round(float(macd_line.iloc[-1]),   4)
            result["macd_signal"]    = round(float(signal_line.iloc[-1]), 4)
            result["macd_histogram"] = round(float((macd_line - signal_line).iloc[-1]), 4)

            # ── 52-week range ──────────────────────────────────────────────
            tail = close.tail(252)
            result["week_52_low"]  = round(float(tail.min()), 2)
            result["week_52_high"] = round(float(tail.max()), 2)

        except Exception:
            logger.debug("Technical fetch failed for %s", ticker, exc_info=True)

    def _fetch_news(self, ticker: str, result: dict) -> None:
        """Latest 5 headlines (Finviz → yfinance fallback)."""
        try:
            from app.services.news_scraper import NewsScraper
            news = NewsScraper().get_stock_news(ticker, limit=5)
            result["news"]         = news[:5]
            result["top_headline"] = news[0]["headline"] if news else "No recent news"
        except Exception:
            logger.debug("News fetch failed for %s", ticker, exc_info=True)

    def _fetch_mongo_history(self, ticker: str, result: dict) -> None:
        """Query MongoDB for previous sentiment scores and cooldown status."""
        try:
            from app.data.mongo_client import MongoDB
            history = MongoDB.get_sentiment_history(ticker, days=30)
            result["sentiment_history"] = history[-5:]
            result["recently_alerted"]  = MongoDB.was_sent_recently(ticker, days=7)
            result["recently_options"]  = MongoDB.was_options_sent_recently(ticker, days=7)
        except Exception:
            logger.debug("MongoDB history fetch failed for %s", ticker, exc_info=True)
