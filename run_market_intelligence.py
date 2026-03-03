"""
Market Intelligence Pipeline — Entry Point
==========================================
Runs the daily sentiment-scoring pipeline:
  1. Builds a full ticker list (training universe + MongoDB institutional picks)
  2. Fetches recent news from Yahoo Finance via yfinance
  3. Scores each ticker's headlines with OpenAI (senior analyst persona)
  4. Stores structured results in MongoDB → daily_market_sentiment

Schedule: run once daily, ideally before market open (e.g., 08:00 ET).

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

# Base training universe (mirrors train_model.py — kept here as single source of truth)
TRAINING_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
    "INTC", "CRM", "ADBE", "ORCL", "NFLX", "PYPL", "SQ", "SHOP",
    "SNAP", "TWLO", "ZM", "DDOG", "NET", "CRWD", "OKTA", "MDB",
    "PLTR", "RBLX", "COIN", "HOOD", "SOFI", "UPST", "AFRM",
    "JPM", "BAC", "GS", "MS", "C", "WFC", "AXP", "V", "MA",
    "XOM", "CVX", "OXY", "SLB", "HAL", "COP", "EOG",
    "PFE", "JNJ", "ABBV", "MRK", "LLY", "AMGN", "BIIB", "GILD", "REGN",
    "DIS", "PARA", "WBD",
    "TEVA", "RKT", "BABA", "BIDU", "NIO", "XPEV",
    "SPY", "QQQ", "IWM",
]


def get_all_tickers() -> list[str]:
    """
    Combine TRAINING_UNIVERSE with any tickers saved in MongoDB
    (institutional picks + news events) so the sentiment pipeline
    automatically covers newly discovered stocks.
    """
    tickers: set[str] = set(TRAINING_UNIVERSE)
    try:
        db = MongoDB.get_db()
        for doc in db["institutional_picks"].find({}, {"ticker": 1}):
            if t := doc.get("ticker"):
                tickers.add(t.upper())
        for doc in db["news_events"].find({}, {"ticker": 1}):
            if t := doc.get("ticker"):
                tickers.add(t.upper())
        logger.info("Total tickers (universe + MongoDB): %d", len(tickers))
    except Exception:
        logger.warning("MongoDB ticker enrichment failed — using base universe only.")
    return sorted(tickers)


def run_market_intelligence():
    logger.info("=== Market Intelligence Pipeline ===")
    tickers = get_all_tickers()
    logger.info("Scoring sentiment for %d tickers...", len(tickers))

    scraper = MarketIntelligenceScraper()
    results = scraper.run(tickers)

    logger.info("Pipeline complete — %d / %d records stored in daily_market_sentiment.",
                len(results), len(tickers))

    # Summary stats
    if results:
        scores = [r["sentiment_score"] for r in results]
        avg_score = sum(scores) / len(scores)
        bullish   = sum(1 for s in scores if s >= 7)
        bearish   = sum(1 for s in scores if s <= 3)
        logger.info(
            "Sentiment summary: avg=%.1f  bullish(≥7)=%d  bearish(≤3)=%d",
            avg_score, bullish, bearish,
        )


if __name__ == "__main__":
    run_market_intelligence()
