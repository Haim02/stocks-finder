"""
Daily Options Brief — Entry Point
===================================
Tastytrade-style options pipeline:

  1. Finviz momentum scans  → bullish + bearish candidates (up to SCAN_LIMIT each)
  2. XGBoost pre-filter     → keep top XGB_POOL by confidence
  3. 4-day cooldown filter  → skip tickers already sent (sent_options collection)
  4. News + company fetch   → headlines + business summary per ticker
  5. OptionsService         → 0DTE SPX iron condor + stock credit spreads
  6. AIService              → Hebrew Tastytrade analyst commentary (with news)
  7. EmailService           → visually styled Daily Options Brief via Resend
  8. Cooldown logging       → record sent tickers to sent_options collection

0DTE SPX methodology:
  - SPY used as SPX proxy (options more accessible via yfinance)
  - Short strikes targeted at 0.10–0.15 delta
  - Spread width: $3 (VIX ≤ 20) / $5 (VIX > 20)
  - Stop-loss at 2× premium, profit target at 50%
  - Minimum 1:3 risk/reward enforced

Schedule: run once daily before market open (e.g., 08:00 ET).

Usage:
    python run_options_scan.py
"""

import logging

import yfinance as yf

from app.data.mongo_client import MongoDB
from app.services.ai_service import AIService
from app.services.api_hub import get_macro_context
from app.services.email_service import EmailService
from app.services.finviz_service import FinvizService
from app.services.ml_service import predict_confidence
from app.services.news_scraper import NewsScraper
from app.services.options_service import OptionsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Pipeline constants ──────────────────────────────────────────────────────
SCAN_LIMIT    = 40   # Finviz candidates fetched per direction
XGB_POOL      = 20   # keep top N by XGBoost before cooldown filter
COOLDOWN_DAYS = 4    # skip tickers sent in an options email in the last N days
TOP_N         = 7    # max final candidates per direction after cooldown
NEWS_LIMIT    = 5    # headlines fetched per ticker (top 3 passed to AI)
BIZ_SUMMARY_CHARS = 350  # max chars of longBusinessSummary to pass to AI


# ── Helper functions ────────────────────────────────────────────────────────

def _score_tickers(tickers: list[str], pool: int) -> list[tuple[float, str]]:
    """
    Run XGBoost on every ticker and return the top `pool` sorted by confidence.
    Tickers with no score (OTC / insufficient data) are pushed to the bottom
    so the pipeline always has fallback candidates.
    """
    scored: list[tuple[float, str]] = []
    unscored: list[str] = []

    for t in tickers:
        conf = predict_confidence(t)
        if conf is not None:
            scored.append((conf, t))
        else:
            unscored.append(t)

    scored.sort(reverse=True)
    combined = scored + [(0.0, t) for t in unscored]
    return combined[:pool]


def _apply_cooldown(
    ranked: list[tuple[float, str]], top_n: int
) -> list[tuple[float, str]]:
    """
    Walk the ranked list and skip any ticker that was included in an options
    email within the last COOLDOWN_DAYS days.  Returns up to top_n survivors.
    """
    result: list[tuple[float, str]] = []
    for conf, t in ranked:
        if MongoDB.was_options_sent_recently(t, days=COOLDOWN_DAYS):
            logger.info("Cooldown skip: %s (sent in last %d days)", t, COOLDOWN_DAYS)
            continue
        result.append((conf, t))
        if len(result) >= top_n:
            break
    return result


def _fetch_ticker_context(ticker: str, scraper: NewsScraper) -> dict:
    """
    Fetch the latest headlines and a brief business description for `ticker`.

    Returns:
        news_headlines   : list[str] — top 3 recent headlines
        business_summary : str       — shortName + sector + truncated description
    """
    # News (Finviz primary, yfinance fallback)
    raw_news = scraper.get_stock_news(ticker, limit=NEWS_LIMIT)
    headlines = [n["headline"] for n in raw_news[:3]]

    # Company info via yfinance
    business_summary = ""
    try:
        info     = yf.Ticker(ticker).info
        name     = info.get("shortName", ticker)
        sector   = info.get("sector", "")
        industry = info.get("industry", "")
        desc     = (info.get("longBusinessSummary") or "")[:BIZ_SUMMARY_CHARS]
        parts    = [p for p in [name, sector, industry] if p]
        business_summary = " · ".join(parts) + (f": {desc}" if desc else "")
    except Exception:
        logger.debug("Could not fetch company info for %s", ticker)

    return {
        "news_headlines":   headlines,
        "business_summary": business_summary,
    }


# ── Main runner ─────────────────────────────────────────────────────────────

def run_options_scan() -> None:
    logger.info("=== Daily Options Brief ===")

    # 1. Momentum scans
    raw_bullish = FinvizService.get_bullish_tickers(n=SCAN_LIMIT)
    raw_bearish = FinvizService.get_bearish_tickers(n=SCAN_LIMIT)

    if not raw_bullish and not raw_bearish:
        logger.warning("No Finviz candidates found — aborting options scan.")
        return

    # 2. XGBoost pre-filter
    bull_ranked = _score_tickers(raw_bullish, XGB_POOL)
    bear_ranked = _score_tickers(raw_bearish, XGB_POOL)

    # 3. 4-day cooldown filter
    bull_final = _apply_cooldown(bull_ranked, TOP_N)
    bear_final = _apply_cooldown(bear_ranked, TOP_N)

    bullish = [t for _, t in bull_final]
    bearish = [t for _, t in bear_final]

    logger.info(
        "After cooldown — Bullish (%d): %s | Bearish (%d): %s",
        len(bullish), ", ".join(bullish) or "none",
        len(bearish), ", ".join(bearish) or "none",
    )

    if not bullish and not bearish:
        logger.warning("All candidates in cooldown — aborting scan.")
        return

    # 4. Fetch news + company context for all surviving tickers
    scraper = NewsScraper()
    ticker_context: dict[str, dict] = {}
    for t in bullish + bearish:
        ctx = _fetch_ticker_context(t, scraper)
        ticker_context[t] = ctx
        logger.info("%s: %d headline(s) fetched", t, len(ctx["news_headlines"]))

    # 5. Build options report (0DTE SPX + stock credit spreads)
    svc    = OptionsService()
    report = svc.build_report(bullish, bearish)

    # Inject FRED macro context so the AI can adjust its strategy recommendation
    macro = get_macro_context()
    report["macro_context"] = macro
    logger.info(
        "Macro context: Fed Rate=%s%%, CPI YoY=%s%%, Regime=%s",
        macro.get("fed_rate", "N/A"),
        macro.get("cpi_yoy",  "N/A"),
        macro.get("regime",   "N/A"),
    )

    # 6. Attach confidence + news + business summary to each stock option entry
    conf_map = {t: c for c, t in bull_final + bear_final}
    for opt in report.get("stock_options", []):
        t = opt["ticker"]
        opt["confidence"]       = conf_map.get(t)
        opt["news_headlines"]   = ticker_context.get(t, {}).get("news_headlines", [])
        opt["business_summary"] = ticker_context.get(t, {}).get("business_summary", "")

    spx_ok   = report["spx_setup"] is not None
    n_stocks = len(report["stock_options"])
    logger.info(
        "Report built — 0DTE: %s | Stocks: %d | SPX: %s | VIX: %s",
        "✓" if spx_ok else "✗",
        n_stocks,
        report["spx_price"],
        report["vix"],
    )

    if not spx_ok and n_stocks == 0:
        logger.warning("No tradeable setups found — skipping email.")
        return

    # 7. AI Tastytrade commentary (Hebrew, enriched with news + business context)
    ai_svc   = AIService()
    analysis = ai_svc.get_options_analysis(report)

    # 8. Send email
    EmailService.send_options_report(report, analysis)

    # 9. Record sent tickers in cooldown collection
    sent_tickers = [opt["ticker"] for opt in report.get("stock_options", [])]
    for t in sent_tickers:
        MongoDB.log_options_sent(t)
    logger.info(
        "Logged %d tickers to sent_options cooldown: %s",
        len(sent_tickers),
        ", ".join(sent_tickers),
    )

    logger.info("=== Daily Options Brief complete ===")


if __name__ == "__main__":
    run_options_scan()
