"""
Hybrid news + technical scan.

Entry point: python run_news_scan.py

Sources:
  - Finviz screener (configured via SCAN_URL)
  - TradingView screener (swap SCAN_URL to a tradingview.com URL)
  - NewsAggregator (RSS biotech/FDA feed)

Decision logic:
  - If a fresh (<3 day) news headline scores ≥ 50  → "News" opportunity
  - Else if a technical signal exists (SMA150 crossover / SMA50 breakout) → "Technical"
  - Stocks already alerted within 3 days are skipped (spam filter).
"""

import logging
import time
from datetime import datetime

import pytz

from app.data.mongo_client import MongoDB
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.financial_service import FinancialAnalyzer
from app.services.ml_service import predict_confidence
from app.services.news_aggregator import NewsAggregator
from app.services.news_model import NewsModel
from app.services.news_scraper import NewsScraper
from app.services.screener_service import ScreenerService
from app.services.tradingview_service import TradingViewService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# --- Configure your scan source here ---
# Option A: Finviz (active)
# SCAN_URL = "https://finviz.com/screener.ashx?v=211&f=sh_avgvol_o500,sh_curvol_o500,sh_relvol_o1,sh_short_o5,ta_beta_o1.5,ta_perf_dup,ta_rsi_nos50,ta_sma20_pa&ft=4"
# SCAN_URL = "https://finviz.com/screener.ashx?v=211&f=sh_avgvol_o400,sh_relvol_o1,sh_short_o5,ta_rsi_nos50,ta_sma50_pc&ft=4"
# SCAN_URL = "https://finviz.com/screener.ashx?v=211&f=sh_avgvol_o400,sh_relvol_o1,sh_short_o5,ta_rsi_nos50&ft=4"
# SCAN_URL = (
#     "https://finviz.com/screener.ashx?v=211"
#     "&f=cap_smallover,sh_avgvol_o500,sh_curvol_o500,sh_relvol_o1,"
#     "sh_short_o5,ta_beta_o1.5,ta_perf_dup,ta_rsi_nos50,ta_sma20_pa,ta_sma50_pa"
#     "&ft=4"
# )
SCAN_URL = "https://finviz.com/screener.ashx?v=211&f=sh_avgvol_o500,sh_curvol_o500,sh_relvol_o1,sh_short_o5,ta_beta_o1.5,ta_perf_dup,ta_rsi_nos50&ft=4"
# Option B: TradingView (uncomment and replace SCAN_URL above)
# SCAN_URL = "https://www.tradingview.com/screener/BmHEGvNM/"

NEWS_SCORE_THRESHOLD = 50
NEWS_FRESHNESS_DAYS = 3
COOLDOWN_DAYS = 3
INTER_TICKER_SLEEP = 1  # seconds


def run_hybrid_scan():
    logger.info("Starting Hybrid Scan (Smart Filter + Date Check)...")

    news_aggregator = NewsAggregator()
    scraper = NewsScraper()
    model = NewsModel()
    fin_analyzer = FinancialAnalyzer()
    ai_service = AIService()

    # --- General market news (RSS) ---
    general_news = news_aggregator.fetch_last_24h_news()

    # --- Collect candidate tickers ---
    target_tickers: set[str] = set()

    if "tradingview.com" in SCAN_URL:
        logger.info("Source: TradingView (Selenium) — extracting tickers only, news from Finviz")
        tickers = TradingViewService.get_candidates_from_url(SCAN_URL)
        if tickers:
            logger.info(
                "Found %d tickers from TradingView, now fetching news from Finviz...",
                len(tickers),
            )
    else:
        logger.info("Source: Finviz")
        tickers = ScreenerService.get_candidates_from_url(SCAN_URL)
        if tickers:
            logger.info("Candidates found: %d", len(tickers))

    if tickers:
        target_tickers.update(tickers)

    # Add biotech / FDA tickers from RSS
    biotech_tickers = news_aggregator.find_biotech_opportunities()
    if biotech_tickers:
        logger.info("Adding %d biotech tickers from RSS.", len(biotech_tickers))
        target_tickers.update(biotech_tickers)

    final_list = list(target_tickers)
    logger.info("Total unique candidates to analyze: %d", len(final_list))

    # Persist candidates so run_market_intelligence.py can scope its work
    MongoDB.save_scanner_candidates(final_list, source="news_scan")

    stock_opportunities: list[dict] = []

    for ticker in final_list:
        # Spam filter
        if MongoDB.was_sent_recently(ticker, days=COOLDOWN_DAYS):
            logger.info("Skipping %s (sent in last %d days).", ticker, COOLDOWN_DAYS)
            continue

        # --- Financial + technical data ---
        fin_data = fin_analyzer.analyze(ticker)
        if not fin_data:
            continue

        technical_signal = fin_data.get("technical_signal")

        # --- News scoring (fresh only) ---
        _, news_items = scraper.get_stock_data(ticker, limit=20)

        news_score = 0
        best_headline = (
            f"איתות טכני: {technical_signal}" if technical_signal else "ללא חדשות"
        )
        real_headline_found = False

        for item in news_items:
            MongoDB.save_news_event(ticker, item)  # store for future training

            pub = item.get("published_at")
            if pub and (datetime.now(pytz.utc) - pub).days > NEWS_FRESHNESS_DAYS:
                continue  # too old

            score = model.predict_impact(item["headline"])
            if score > news_score:
                news_score = score
                best_headline = item["headline"]
                real_headline_found = True

        # --- Decision ---
        should_add = False
        reason = ""

        if news_score >= NEWS_SCORE_THRESHOLD:
            should_add = True
            reason = "News"
        elif technical_signal:
            should_add = True
            reason = "Technical"
            if not real_headline_found:
                news_score = 55  # baseline score for pure-technical picks

        if not should_add:
            time.sleep(INTER_TICKER_SLEEP)
            continue

        logger.info("Opportunity found: %s (%s)", ticker, reason)
        MongoDB.log_sent_alert(ticker, reason)

        # XGBoost confidence score
        confidence = predict_confidence(ticker)
        if confidence is not None:
            logger.info("XGBoost confidence %s: %.1f%%", ticker, confidence)

        # AI analysis (Goldman Sachs framework — enriched financials auto-passed)
        prompt_headline = best_headline
        if reason == "Technical" and not real_headline_found:
            prompt_headline = f"Technical Signal: {technical_signal}. Company analysis needed."

        ai_result = ai_service.analyze_stock(ticker, prompt_headline, fin_data)

        stock_opportunities.append(
            {
                "ticker": ticker,
                "headline": best_headline,
                "score": news_score,
                "price": fin_data["current_price"],
                "confidence": confidence,
                "financials": fin_data,
                "ai_hebrew_desc": ai_result["hebrew_desc"],
                "ai_analysis": ai_result["analysis"],
            }
        )

        time.sleep(INTER_TICKER_SLEEP)

    # --- Send report ---
    if stock_opportunities or general_news:
        stock_opportunities.sort(key=lambda x: x["score"], reverse=True)
        logger.info(
            "Sending report: %d stocks, %d headlines.",
            len(stock_opportunities),
            len(general_news),
        )
        EmailService.send_report(stock_opportunities, general_news)
    else:
        logger.info("No new opportunities found (spam filter active).")


if __name__ == "__main__":
    run_hybrid_scan()
