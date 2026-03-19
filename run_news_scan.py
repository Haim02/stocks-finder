"""
Hybrid news + technical scan.

Entry point:
    python run_news_scan.py                  # both sources (default)
    python run_news_scan.py --source finviz  # Finviz only
    python run_news_scan.py --source tv      # TradingView only
    python run_news_scan.py --source both    # merge both, dedup tickers + headlines

Sources:
  - finviz : Finviz screener (cloudscraper, multi-page, no Selenium)
  - tv     : TradingView screener (Selenium + Chrome)
  - both   : union of the two — identical tickers and duplicate headlines
             are removed before the AI sees any data

Decision logic:
  - Fresh (<3 day) headline scoring ≥ 50   → "News" opportunity
  - Else technical signal present           → "Technical" opportunity
  - Stocks already alerted within 3 days   → skipped (spam filter)
"""

import argparse
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


# ── Screener URLs — all edits belong here, never buried inside functions ──────
SCAN_SOURCES: dict[str, str] = {
    "finviz": (
        "https://finviz.com/screener.ashx?v=211&f=sh_avgvol_o400,sh_relvol_o1.5,sh_short_o5,ta_beta_o0.5,ta_rsi_nos50&ft=4"
    ),
    "tv": "https://www.tradingview.com/screener/BmHEGvNM/",
}

NEWS_SCORE_THRESHOLD = 50
NEWS_FRESHNESS_DAYS  = 3
COOLDOWN_DAYS        = 3
INTER_TICKER_SLEEP   = 1  # seconds between ticker API calls


# ── Source routing ─────────────────────────────────────────────────────────────

def _collect_tickers(source: str) -> set[str]:
    """
    Collect candidate tickers from the requested source(s).

    source   result
    ───────  ────────────────────────────────────────────────────────
    finviz   Finviz screener only
    tv       TradingView screener only (requires Chrome + Selenium)
    both     Set-union of both screeners — duplicate tickers removed
    """
    tickers: set[str] = set()

    if source in ("finviz", "both"):
        fv = ScreenerService.get_candidates_from_url(SCAN_SOURCES["finviz"])
        logger.info("[Finviz]      %d tickers", len(fv))
        tickers.update(fv)

    if source in ("tv", "both"):
        tv = TradingViewService.get_candidates_from_url(SCAN_SOURCES["tv"])
        logger.info("[TradingView] %d tickers", len(tv))
        tickers.update(tv)

    if source == "both":
        logger.info("[Merge]       %d unique tickers after dedup", len(tickers))

    return tickers


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_hybrid_scan(source: str = "both") -> str:
    """
    Run the hybrid news + technical scan.

    Args:
        source: "finviz" | "tv" | "both"  (default "both")

    Returns:
        Plain-text one-line summary — displayed in Telegram after the run.
    """
    logger.info("═══ Hybrid Scan — source: %s ═══", source.upper())

    news_aggregator = NewsAggregator()
    scraper         = NewsScraper()
    model           = NewsModel()
    fin_analyzer    = FinancialAnalyzer()
    ai_service      = AIService()

    # General market news (RSS biotech/FDA/macro)
    general_news = news_aggregator.fetch_last_24h_news()

    # Collect tickers — dedup via set union
    target_tickers = _collect_tickers(source)

    # Append biotech / FDA tickers from RSS feed
    biotech_tickers = news_aggregator.find_biotech_opportunities()
    if biotech_tickers:
        logger.info("[RSS] Adding %d biotech tickers", len(biotech_tickers))
        target_tickers.update(biotech_tickers)

    final_list = list(target_tickers)
    logger.info("Total unique candidates: %d", len(final_list))

    # Persist for the market-intelligence pipeline (48h window)
    MongoDB.save_scanner_candidates(final_list, source=f"news_scan_{source}")

    stock_opportunities: list[dict] = []

    for ticker in final_list:
        # Spam / cooldown filter
        if MongoDB.was_sent_recently(ticker, days=COOLDOWN_DAYS):
            logger.info("Skip %s (cooldown %dd)", ticker, COOLDOWN_DAYS)
            continue

        fin_data = fin_analyzer.analyze(ticker)
        if not fin_data:
            continue

        technical_signal = fin_data.get("technical_signal")

        # Fetch news then deduplicate headlines
        # (a ticker that appears on both screeners would otherwise get
        #  duplicate headlines fed to the model — this prevents that)
        _, raw_news = scraper.get_stock_data(ticker, limit=20)
        seen: set[str] = set()
        news_items: list[dict] = []
        for item in raw_news:
            h = item.get("headline", "").strip()
            if h and h not in seen:
                seen.add(h)
                news_items.append(item)

        news_score          = 0
        best_headline       = (
            f"איתות טכני: {technical_signal}" if technical_signal else "ללא חדשות"
        )
        real_headline_found = False

        for item in news_items:
            MongoDB.save_news_event(ticker, item)

            pub = item.get("published_at")
            if pub and (datetime.now(pytz.utc) - pub).days > NEWS_FRESHNESS_DAYS:
                continue

            score = model.predict_impact(item["headline"])
            if score > news_score:
                news_score          = score
                best_headline       = item["headline"]
                real_headline_found = True

        # Decision gate
        if news_score >= NEWS_SCORE_THRESHOLD:
            reason = "News"
        elif technical_signal:
            reason = "Technical"
            if not real_headline_found:
                news_score = 55  # baseline for pure-technical picks
        else:
            time.sleep(INTER_TICKER_SLEEP)
            continue

        logger.info("Opportunity: %s (%s, score=%d)", ticker, reason, news_score)
        MongoDB.log_sent_alert(ticker, reason)

        confidence = predict_confidence(ticker)
        if confidence is not None:
            logger.info("XGBoost %s: %.1f%%", ticker, confidence)

        prompt_headline = best_headline
        if reason == "Technical" and not real_headline_found:
            prompt_headline = (
                f"Technical Signal: {technical_signal}. Company analysis needed."
            )

        ai_result = ai_service.analyze_stock(ticker, prompt_headline, fin_data)

        stock_opportunities.append({
            "ticker":         ticker,
            "headline":       best_headline,
            "score":          news_score,
            "price":          fin_data["current_price"],
            "confidence":     confidence,
            "financials":     fin_data,
            "ai_hebrew_desc": ai_result["hebrew_desc"],
            "ai_analysis":    ai_result["analysis"],
        })

        time.sleep(INTER_TICKER_SLEEP)

    # Send email report
    if stock_opportunities or general_news:
        stock_opportunities.sort(key=lambda x: x["score"], reverse=True)
        logger.info(
            "Sending report: %d stocks, %d RSS headlines",
            len(stock_opportunities), len(general_news),
        )
        EmailService.send_report(stock_opportunities, general_news)
    else:
        logger.info("No new opportunities found (spam filter active).")

    summary = (
        f"סריקה ({source}) הושלמה — "
        f"{len(stock_opportunities)} הזדמנויות, "
        f"{len(final_list)} מניות נסרקו."
    )
    logger.info(summary)
    return summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Hybrid news + technical stock scan",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python run_news_scan.py                  # both (default)\n"
            "  python run_news_scan.py --source finviz  # Finviz only\n"
            "  python run_news_scan.py --source tv      # TradingView only\n"
        ),
    )
    p.add_argument(
        "--source",
        choices=["finviz", "tv", "both"],
        default="both",
        help="Screener source (default: both)",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run_hybrid_scan(source=args.source)
