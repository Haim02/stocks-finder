"""
perplexity_service.py — Real-Time Internet Access for the Agent
===============================================================

Perplexity = the agent's eyes on the real world.
Without this, the agent is blind to:
- Breaking news
- Earnings results
- Fed decisions
- Analyst upgrades/downgrades
- Product launches
- M&A rumors
- Anything that happened today

This service makes the agent aware of the real world in real-time.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"

# Cache — avoid duplicate searches
_cache: dict = {}
_CACHE_TTL = 900  # 15 minutes


def _cached_search(query: str) -> Optional[str]:
    cached = _cache.get(query)
    if cached:
        result, ts = cached
        if time.time() - ts < _CACHE_TTL:
            return result
    return None


def _set_cache(query: str, result: str):
    _cache[query] = (result, time.time())


# ── Backward compat dataclass (used by market_regime_agent) ──────────────────

@dataclass
class PerplexityResearch:
    macro_events: str
    fed_commentary: str
    market_sentiment: str
    sp500_risks: str
    raw_responses: dict
    has_data: bool


class PerplexityService:

    def is_available(self) -> bool:
        return bool(PERPLEXITY_API_KEY)

    def search(self, query: str, max_chars: int = 500) -> str:
        """
        Search the real-time internet.
        Returns clean Hebrew-friendly answer.
        """
        if not self.is_available():
            return ""

        cached = _cached_search(query)
        if cached:
            return cached

        try:
            headers = {
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": PERPLEXITY_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a financial research assistant. "
                            "Answer concisely with the most current facts. "
                            "Focus on: prices, news, earnings, analyst ratings, catalysts. "
                            "If asked in Hebrew context, keep financial terms in English."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                "max_tokens": 400,
                "temperature": 0.1,
                "search_recency_filter": "day",  # Today's news only
                "return_citations": False,
            }
            resp = requests.post(
                PERPLEXITY_URL, headers=headers,
                json=payload, timeout=15
            )
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"].strip()
            if answer:
                _set_cache(query, answer)
                return answer[:max_chars]
        except Exception as e:
            logger.warning("Perplexity search failed: %s", e)
        return ""

    # ── Backward compatibility alias (used by smart_scanner, free_chat, news_command) ─

    def ask(self, question: str) -> str:
        """Alias for search() — backward compatible."""
        return self.search(question)

    # ── Backward compat: morning research (used by market_regime_agent) ───────

    def run_morning_research(self) -> PerplexityResearch:
        """Run 4 morning research queries for Agent 1."""
        if not self.is_available():
            return PerplexityResearch(
                macro_events="", fed_commentary="",
                market_sentiment="", sp500_risks="",
                raw_responses={}, has_data=False,
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
        raw = {key: self.search(q, max_chars=600) for key, q in queries.items()}
        logger.info("Perplexity morning research complete (%d chars total)",
                    sum(len(v) for v in raw.values()))
        return PerplexityResearch(
            macro_events=raw.get("macro_events", ""),
            fed_commentary=raw.get("fed_commentary", ""),
            market_sentiment=raw.get("market_sentiment", ""),
            sp500_risks=raw.get("sp500_risks", ""),
            raw_responses=raw,
            has_data=any(v for v in raw.values()),
        )

    # ── Specialized search methods ──────────────────────────────────────────

    def why_is_stock_moving(self, ticker: str, move_pct: float) -> str:
        """Why is this stock moving today?"""
        direction = "rising" if move_pct > 0 else "falling"
        return self.search(
            f"Why is {ticker} stock {direction} today ({move_pct:+.1f}%)? "
            f"What is the specific catalyst? Earnings, news, analyst, M&A? "
            f"Be specific and factual. 3 sentences max."
        )

    def get_stock_news(self, ticker: str) -> str:
        """Latest news for a stock."""
        return self.search(
            f"What are the latest news and developments for {ticker} stock "
            f"in the past 7 days? Include: earnings, product launches, "
            f"analyst ratings, partnerships. Bullet points."
        )

    def get_earnings_result(self, ticker: str) -> str:
        """Latest earnings results."""
        return self.search(
            f"What were {ticker}'s most recent quarterly earnings results? "
            f"EPS vs estimate, revenue vs estimate, guidance, stock reaction."
        )

    def get_sector_rotation(self) -> str:
        """What sectors are hot this week?"""
        return self.search(
            f"What sectors and industries are outperforming the market this week? "
            f"Which sectors are rotating into? Which are rotating out of? "
            f"Include specific ETFs and reasons."
        )

    def get_macro_today(self) -> str:
        """Today's macro events."""
        from datetime import date
        today = date.today().strftime("%B %d, %Y")
        return self.search(
            f"Today is {today}. What are the key macro events happening today? "
            f"Fed speakers, economic data releases (CPI, PPI, jobs), "
            f"Treasury auctions, major earnings. Be specific with times."
        )

    def get_options_flow(self, ticker: str) -> str:
        """Unusual options activity."""
        return self.search(
            f"Is there unusual options activity or dark pool prints for {ticker} recently? "
            f"Any large block trades, unusual call/put volume, or smart money positioning?"
        )

    def get_analyst_changes(self, ticker: str) -> str:
        """Recent analyst upgrades/downgrades."""
        return self.search(
            f"What are the most recent analyst rating changes for {ticker}? "
            f"Include: firm name, old rating, new rating, price target, date."
        )

    def get_next_big_trend(self) -> str:
        """What's the next big market trend?"""
        return self.search(
            f"What are the top 3 emerging investment themes and trends "
            f"that institutional investors and hedge funds are focusing on right now? "
            f"Include specific sectors, companies, and catalysts."
        )

    def search_for_csp_candidates(self, max_price: float) -> str:
        """Find CSP-worthy stocks under a price."""
        return self.search(
            f"What are liquid, optionable US stocks priced under ${max_price} "
            f"with high implied volatility and bullish momentum right now? "
            f"These are for selling Cash Secured Puts. "
            f"List 5-8 tickers with price and reason."
        )
