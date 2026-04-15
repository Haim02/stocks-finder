"""
perplexity_service.py — Perplexity Sonar API Client
=====================================================

Provides focused real-time market research queries using Perplexity's
Sonar model. Used by Agent 1 (Market Regime Analyst) every morning.

Model used: sonar (cheapest, fast, real-time web access)
~4 queries/day = ~$0.002/day = ~$0.06/month

API is OpenAI-compatible — uses the openai Python client pointed at
Perplexity's base URL.

Setup:
    Set PERPLEXITY_API_KEY in environment variables / Render dashboard.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL    = "sonar"          # cheapest + real-time web
MAX_TOKENS          = 300              # keep answers short and focused


@dataclass
class PerplexityResearch:
    macro_events: str       # significant economic events today
    fed_commentary: str     # what the Fed said recently
    market_sentiment: str   # risk-on / risk-off sentiment
    sp500_risks: str        # major negative news for S&P 500
    raw_responses: dict     # full text per query key
    has_data: bool          # False if API key missing or all calls failed


def _query(client, question: str) -> str:
    """Send a single focused question to Perplexity Sonar."""
    try:
        response = client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise financial market analyst. "
                        "Answer in 2-4 bullet points maximum. "
                        "Focus only on facts relevant to US stock market trading. "
                        "Today's date is relevant — use real-time web data."
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=MAX_TOKENS,
            timeout=15.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Perplexity query failed: %s | Question: %s", e, question[:60])
        return ""


class PerplexityService:
    """
    Runs 4 focused market research queries every morning.

    Usage:
        svc = PerplexityService()
        if svc.is_available():
            research = svc.run_morning_research()
    """

    def __init__(self):
        self._api_key = os.getenv("PERPLEXITY_API_KEY")
        self._client = None
        if self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=PERPLEXITY_BASE_URL,
                )
                logger.info("PerplexityService initialized (model=%s)", PERPLEXITY_MODEL)
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
        else:
            logger.warning(
                "PERPLEXITY_API_KEY not set — Perplexity research disabled. "
                "Set the key in Render environment variables to enable."
            )

    def is_available(self) -> bool:
        return self._client is not None

    def run_morning_research(self) -> PerplexityResearch:
        """
        Run all 4 morning research queries.
        Returns PerplexityResearch with has_data=False if unavailable.
        """
        if not self.is_available():
            return PerplexityResearch(
                macro_events="",
                fed_commentary="",
                market_sentiment="",
                sp500_risks="",
                raw_responses={},
                has_data=False,
            )

        logger.info("Running Perplexity morning research (4 queries)...")

        queries = {
            "macro_events": (
                "What are the most significant macroeconomic events, data releases, "
                "or central bank decisions happening today or this week that affect US stock markets?"
            ),
            "fed_commentary": (
                "What has the Federal Reserve said most recently about interest rates, "
                "inflation, or monetary policy? Any Fed officials speaking today?"
            ),
            "market_sentiment": (
                "What is the current US stock market sentiment today — "
                "risk-on or risk-off? What are institutional investors doing?"
            ),
            "sp500_risks": (
                "Are there any major negative news events, geopolitical risks, "
                "or earnings surprises today that could significantly impact the S&P 500?"
            ),
        }

        raw = {}
        for key, question in queries.items():
            raw[key] = _query(self._client, question)
            logger.info("Perplexity [%s]: %d chars", key, len(raw[key]))

        return PerplexityResearch(
            macro_events=raw.get("macro_events", ""),
            fed_commentary=raw.get("fed_commentary", ""),
            market_sentiment=raw.get("market_sentiment", ""),
            sp500_risks=raw.get("sp500_risks", ""),
            raw_responses=raw,
            has_data=any(v for v in raw.values()),
        )

    def ask(self, question: str) -> str:
        """
        Ask any free-form question. Used by free_chat.py when Haim
        asks: "מה אמר הפד היום?" or "האם יש חדשות רעות על NVDA?"

        Returns empty string if unavailable.
        """
        if not self.is_available():
            return ""
        return _query(self._client, question)
