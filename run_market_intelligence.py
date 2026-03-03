"""
Market Intelligence Pipeline — Entry Point
==========================================
Runs the daily sentiment-scoring pipeline:
  1. Fetches tickers that appeared in any screener (Finviz / TradingView /
     Smart Money) within the last 48 hours from MongoDB scanner_candidates.
  2. Fetches recent news from Yahoo Finance via yfinance.
  3. Scores each ticker's headlines with OpenAI (senior analyst persona).
  4. Stores structured results in MongoDB → daily_market_sentiment.

Why only recent scanner candidates?
  The full training universe contains ~900 tickers.  Scoring them all via
  yfinance + OpenAI every day is unnecessarily slow and expensive.  By
  scoping the pipeline to tickers that the screener *already flagged as
  interesting*, we score the ~20-80 stocks that actually matter for the
  next trading session and finish in minutes instead of hours.

Pre-requisite: at least one of the following must have run in the last 48h:
  python run_news_scan.py       (saves source="news_scan")
  python run_smart_money.py     (saves source="smart_money")

Fallback: if no candidates are found (first run / DB empty), a small
  core watchlist is used so the pipeline is never a no-op.

Schedule: run after each scan (or on a cron, e.g., 08:30 ET daily).

Usage:
    python run_market_intelligence.py
"""

import logging

from app.data.mongo_client import MongoDB
from app.services.market_intelligence_scraper import MarketIntelligenceScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Minimal fallback used only when no scanner has run recently.
# Keep it small — these are the highest-liquidity names worth monitoring daily.
CORE_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD",
    "JPM", "V", "SPY", "QQQ",
]
CANDIDATE_WINDOW_HOURS = 48


def get_candidate_tickers() -> list[str]:
    """
    Returns tickers to score, in priority order:
      1. Tickers seen by any screener in the last 48 hours (primary path).
      2. CORE_WATCHLIST fallback when the DB has no recent candidates.
    """
    try:
        recent = MongoDB.get_recent_scanner_candidates(hours=CANDIDATE_WINDOW_HOURS)
    except Exception:
        logger.warning("Could not reach MongoDB — falling back to core watchlist.")
        return sorted(CORE_WATCHLIST)

    if recent:
        logger.info(
            "Found %d scanner candidates from the last %dh.",
            len(recent), CANDIDATE_WINDOW_HOURS,
        )
        return recent

    logger.warning(
        "No scanner candidates found in the last %dh. "
        "Run run_news_scan.py or run_smart_money.py first. "
        "Falling back to core watchlist (%d tickers).",
        CANDIDATE_WINDOW_HOURS, len(CORE_WATCHLIST),
    )
    return sorted(CORE_WATCHLIST)


def run_market_intelligence():
    logger.info("=== Market Intelligence Pipeline ===")

    tickers = get_candidate_tickers()
    logger.info("Scoring sentiment for %d tickers...", len(tickers))

    scraper = MarketIntelligenceScraper()
    results = scraper.run(tickers)

    logger.info(
        "Pipeline complete — %d / %d records stored in daily_market_sentiment.",
        len(results), len(tickers),
    )

    if results:
        scores    = [r["sentiment_score"] for r in results]
        avg_score = sum(scores) / len(scores)
        bullish   = sum(1 for s in scores if s >= 7)
        bearish   = sum(1 for s in scores if s <= 3)
        logger.info(
            "Sentiment summary: avg=%.1f  bullish(≥7)=%d  bearish(≤3)=%d",
            avg_score, bullish, bearish,
        )


if __name__ == "__main__":
    run_market_intelligence()
