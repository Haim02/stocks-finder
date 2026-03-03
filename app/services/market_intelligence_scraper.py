"""
Market Intelligence Scraper
============================
Fetches recent news headlines for tracked tickers via yfinance, sends them
to OpenAI (acting as a senior financial analyst), and stores a structured
daily sentiment record in MongoDB → collection: daily_market_sentiment.

Document schema:
  {
    ticker         : str   (e.g. "SCCO")
    date           : str   (YYYY-MM-DD, used as upsert key with ticker)
    sentiment_score: float (1 = very bearish … 10 = very bullish)
    key_event_type : str   (earnings|fda_approval|macro|technical|insider|
                            guidance|analyst_upgrade|analyst_downgrade|
                            merger_acquisition|legal|product_launch|other)
    impact_duration: str   (short|long)
    llm_confidence : float (0–1)
    headlines      : list[str]
    scored_at      : datetime
  }

Run via:  python run_market_intelligence.py
"""

import json
import logging
import time
from datetime import date, datetime

import pytz
import yfinance as yf
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.data.mongo_client import MongoDB

logger = logging.getLogger(__name__)

_OPENAI_TRANSIENT = (RateLimitError, APIConnectionError, APITimeoutError)

SENTIMENT_MODEL    = "gpt-4o-mini"
MAX_HEADLINES      = 10
INTER_TICKER_SLEEP = 1.0  # seconds between tickers (rate-limit courtesy)

VALID_EVENT_TYPES = {
    "earnings", "fda_approval", "macro", "technical", "insider",
    "guidance", "analyst_upgrade", "analyst_downgrade",
    "merger_acquisition", "legal", "product_launch", "other",
}


def _build_sentiment_prompt(ticker: str, headlines: list[str]) -> str:
    numbered = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))
    return f"""You are a senior quantitative financial analyst.

Analyze the following {len(headlines)} recent news headlines for stock ticker {ticker}:

{numbered}

Output a single JSON object with EXACTLY these keys:
- "sentiment_score": float from 1 (very bearish) to 10 (very bullish), reflecting the combined market impact
- "key_event_type": dominant event category — one of: earnings, fda_approval, macro, technical, insider, guidance, analyst_upgrade, analyst_downgrade, merger_acquisition, legal, product_launch, other
- "impact_duration": "short" (days to weeks) or "long" (months or more)
- "confidence": float 0–1, your confidence in this assessment

Output ONLY the JSON object. No markdown, no explanation."""


class MarketIntelligenceScraper:
    """Daily sentiment scoring pipeline: news → LLM → MongoDB."""

    def __init__(self):
        self.client: OpenAI | None = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            logger.warning("OPENAI_API_KEY not set — sentiment scoring will be skipped.")

    # ------------------------------------------------------------------
    # News fetching
    # ------------------------------------------------------------------

    def fetch_headlines(self, ticker: str) -> list[str]:
        """Returns up to MAX_HEADLINES recent headlines from yfinance."""
        try:
            news_items = yf.Ticker(ticker).news or []
            headlines: list[str] = []
            for item in news_items[:MAX_HEADLINES]:
                # yfinance returns 'title' (v0.2+) or 'headline' (older builds)
                title = item.get("title") or item.get("headline", "")
                if title:
                    headlines.append(title.strip())
            logger.debug("Fetched %d headlines for %s", len(headlines), ticker)
            return headlines
        except Exception:
            logger.warning("Failed to fetch headlines for %s", ticker, exc_info=True)
            return []

    # ------------------------------------------------------------------
    # LLM scoring
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(_OPENAI_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
    )
    def _call_llm(self, ticker: str, headlines: list[str]) -> dict:
        """Raw OpenAI call with tenacity retry on transient errors."""
        if not self.client:
            return {}
        prompt = _build_sentiment_prompt(ticker, headlines)
        response = self.client.chat.completions.create(
            model=SENTIMENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _score_headlines(self, ticker: str, headlines: list[str]) -> dict | None:
        """Score headlines with LLM. Returns validated dict or None."""
        if not self.client:
            return None
        try:
            raw = self._call_llm(ticker, headlines)
        except Exception:
            logger.warning("LLM scoring failed for %s", ticker, exc_info=True)
            return None

        # Validate required fields
        if not isinstance(raw.get("sentiment_score"), (int, float)):
            logger.warning("LLM returned invalid sentiment_score for %s: %s", ticker, raw)
            return None

        # Sanitise event type
        event_type = str(raw.get("key_event_type", "other")).lower()
        if event_type not in VALID_EVENT_TYPES:
            event_type = "other"

        impact = str(raw.get("impact_duration", "short")).lower()
        if impact not in ("short", "long"):
            impact = "short"

        return {
            "sentiment_score": float(raw["sentiment_score"]),
            "key_event_type":  event_type,
            "impact_duration": impact,
            "llm_confidence":  float(raw.get("confidence", 0.5)),
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def score_ticker(self, ticker: str) -> dict | None:
        """
        Full pipeline for a single ticker:
          fetch headlines → score with LLM → store in MongoDB.
        Returns the stored document, or None on failure / no news.
        """
        headlines = self.fetch_headlines(ticker)
        if not headlines:
            logger.info("No headlines for %s — skipping.", ticker)
            return None

        sentiment = self._score_headlines(ticker, headlines)
        if not sentiment:
            return None

        today_str = date.today().strftime("%Y-%m-%d")
        doc = {
            "ticker":          ticker.upper(),
            "date":            today_str,
            "sentiment_score": sentiment["sentiment_score"],
            "key_event_type":  sentiment["key_event_type"],
            "impact_duration": sentiment["impact_duration"],
            "llm_confidence":  sentiment["llm_confidence"],
            "headlines":       headlines,
            "scored_at":       datetime.now(pytz.utc),
        }

        MongoDB.save_daily_sentiment(doc)
        logger.info(
            "%-6s  score=%.1f  type=%-20s  duration=%s  conf=%.2f",
            ticker,
            doc["sentiment_score"],
            doc["key_event_type"],
            doc["impact_duration"],
            doc["llm_confidence"],
        )
        return doc

    def run(self, tickers: list[str]) -> list[dict]:
        """
        Score sentiment for all tickers sequentially.
        Returns the list of successfully stored documents.
        """
        results: list[dict] = []
        for ticker in tickers:
            result = self.score_ticker(ticker)
            if result:
                results.append(result)
            time.sleep(INTER_TICKER_SLEEP)

        logger.info(
            "Market Intelligence complete: %d / %d tickers scored.",
            len(results), len(tickers),
        )
        return results
