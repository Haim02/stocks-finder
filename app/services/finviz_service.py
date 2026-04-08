"""
Finviz scanner + fundamentals/news/insider helper.

  FinvizService        -- momentum screener (bullish / bearish tickers)
  get_stock_context()  -- per-ticker fundamentals, news & insider summary
  format_context_block() -- renders context dict as Hebrew Telegram Markdown
"""

import logging

from app.services.screener_service import ScreenerService

logger = logging.getLogger(__name__)

_BASE = "https://finviz.com/screener.ashx?v=211&ft=4"

BULLISH_URL = (
    f"{_BASE}"
    "&f=ta_perf_curr_up,ta_sma20_pa,ta_sma50_pa,ta_sma200_pa,sh_avgvol_o500"
)
BEARISH_URL = (
    f"{_BASE}"
    "&f=ta_perf_curr_dn,ta_sma20_pb,ta_sma50_pb,ta_sma200_pb,sh_avgvol_o500"
)


# ── Screener ───────────────────────────────────────────────────────────────────

class FinvizService:
    """Momentum scans used to seed the options pipeline."""

    # Volume-sorted URL fallbacks
    _BULLISH_VOL_URL = (
        "https://finviz.com/screener.ashx?v=111&ft=4"
        "&f=sh_avgvol_o500,sh_price_o5,ta_rsi_nos50,ta_sma20_pa,ta_sma50_pa&o=-volume"
    )
    _BEARISH_VOL_URL = (
        "https://finviz.com/screener.ashx?v=111&ft=4"
        "&f=sh_avgvol_o500,sh_price_o5,ta_rsi_ob60,ta_sma20_pb,ta_sma50_pb&o=-volume"
    )

    _BULLISH_FALLBACK = [
        "NVDA","AAPL","MSFT","META","AMZN","GOOGL","TSLA","AMD",
        "NFLX","CRWD","SNOW","PLTR","COIN","HOOD","SOFI",
        "JPM","BAC","GS","V","MA","XOM","CVX","OXY",
    ]
    _BEARISH_FALLBACK = [
        "INTC","BA","NKE","SBUX","PFE","T","VZ",
        "DIS","PYPL","SQ","WBA","CVS","PARA","WBD",
    ]

    @staticmethod
    def _daily_page_offset(num_pages: int = 6) -> int:
        import datetime
        return (datetime.date.today().timetuple().tm_yday % num_pages) * 20

    @staticmethod
    def get_bullish_tickers(n: int = 40) -> list[str]:
        """
        Fetch bullish tickers — tries finvizfinance Overview first (volume-ranked),
        then cloudscraper with daily page rotation, then hardcoded fallback.
        Never returns alphabetically biased results.
        """
        import random
        logger.info("Finviz bullish scan (target=%d)...", n)

        # 1. finvizfinance Overview API (best — volume-ranked, diverse)
        try:
            from finvizfinance.screener.overview import Overview
            ov = Overview()
            ov.set_filter(
                signal="Top Gainers",
                filters_dict={"Average Volume": "Over 500K", "Price": "Over $5"},
            )
            df = ov.screener_view()
            if df is not None and not df.empty:
                col = next((c for c in ("Ticker", "ticker", "Symbol") if c in df.columns), None)
                if col:
                    tickers = [str(t).upper() for t in df[col].dropna().tolist()]
                    if len(tickers) >= 5:
                        random.shuffle(tickers)
                        logger.info("Bullish (Overview): %d tickers", len(tickers))
                        return tickers[:n]
        except Exception as e:
            logger.debug("Overview bullish failed: %s", e)

        # 2. Cloudscraper with daily page rotation + volume sort
        try:
            offset  = FinvizService._daily_page_offset(6)
            url     = FinvizService._BULLISH_VOL_URL + f"&r={offset + 1}"
            tickers = ScreenerService.get_candidates_from_url(url, limit=n)
            if len(tickers) >= 5:
                random.shuffle(tickers)
                logger.info("Bullish (URL offset=%d): %d tickers", offset, len(tickers))
                return tickers[:n]
        except Exception as e:
            logger.debug("URL bullish failed: %s", e)

        # 3. Hardcoded diverse fallback
        tickers = list(FinvizService._BULLISH_FALLBACK)
        random.shuffle(tickers)
        logger.warning("Bullish: using hardcoded fallback (%d tickers)", len(tickers))
        return tickers[:n]

    @staticmethod
    def get_bearish_tickers(n: int = 20) -> list[str]:
        """
        Fetch bearish tickers — same 3-tier approach as get_bullish_tickers.
        """
        import random
        logger.info("Finviz bearish scan (target=%d)...", n)

        try:
            from finvizfinance.screener.overview import Overview
            ov = Overview()
            ov.set_filter(
                signal="Top Losers",
                filters_dict={"Average Volume": "Over 500K", "Price": "Over $5"},
            )
            df = ov.screener_view()
            if df is not None and not df.empty:
                col = next((c for c in ("Ticker", "ticker", "Symbol") if c in df.columns), None)
                if col:
                    tickers = [str(t).upper() for t in df[col].dropna().tolist()]
                    if len(tickers) >= 3:
                        random.shuffle(tickers)
                        logger.info("Bearish (Overview): %d tickers", len(tickers))
                        return tickers[:n]
        except Exception as e:
            logger.debug("Overview bearish failed: %s", e)

        try:
            offset  = FinvizService._daily_page_offset(4)
            url     = FinvizService._BEARISH_VOL_URL + f"&r={offset + 1}"
            tickers = ScreenerService.get_candidates_from_url(url, limit=n)
            if len(tickers) >= 3:
                random.shuffle(tickers)
                return tickers[:n]
        except Exception as e:
            logger.debug("URL bearish failed: %s", e)

        tickers = list(FinvizService._BEARISH_FALLBACK)
        random.shuffle(tickers)
        logger.warning("Bearish: using hardcoded fallback (%d tickers)", len(tickers))
        return tickers[:n]

    @staticmethod
    def get_candidates_from_url(url: str, limit: int = 20) -> list[str]:
        """Legacy compatibility shim."""
        return ScreenerService.get_candidates_from_url(url, limit=limit)


# ── Fundamentals / news / insider context ──────────────────────────────────────

def get_stock_context(ticker: str) -> dict:
    """
    Fetch fundamental context, latest news, and insider activity for a ticker.

    Returns a dict with:
      target_price    : str  -- analyst price target (e.g. "195.00")
      recommendation  : str  -- analyst mean rating 1-5 (1=Strong Buy)
      latest_news     : list -- up to 3 dicts {date, title}
      insider_trading : str  -- Hebrew summary of recent insider transactions
      massive_selling : bool -- True if >=3 insider sales and sells > 2x buys
      error           : str | None

    Safe to call even if Finviz rate-limits (returns error key, never raises).
    """
    try:
        from finvizfinance.quote import finvizfinance as fvf
        stock = fvf(ticker)

        # Fundamentals
        try:
            fund         = stock.ticker_fundament()
            target_price = fund.get("Target Price", "N/A")
            recom        = fund.get("Recom", "N/A")
        except Exception:
            target_price, recom = "N/A", "N/A"

        # News
        news_list: list[dict] = []
        try:
            news_df = stock.ticker_news()
            for _, row in news_df.head(3).iterrows():
                date_val = row.get("Date", "")
                date_str = (
                    date_val.strftime("%d/%m")
                    if hasattr(date_val, "strftime")
                    else str(date_val)[:10]
                )
                title = (
                    str(row.get("Title", ""))
                    .replace("\r\n", " ")
                    .replace("\n", " ")
                    .strip()[:120]
                )
                if title:
                    news_list.append({"date": date_str, "title": title})
        except Exception:
            pass

        # Insider activity
        buys = sells = 0
        try:
            ins_df = stock.ticker_inside_trader()
            for _, row in ins_df.iterrows():
                txn = str(row.get("Transaction", "")).lower()
                if "buy" in txn or "purchase" in txn:
                    buys += 1
                elif "sale" in txn or "sell" in txn:
                    sells += 1
        except Exception:
            pass

        if buys > 0 and buys > sells:
            insider_summary = f"\U0001f7e2 קנייה ({buys} עסקאות)"
        elif sells > 0 and sells >= buys:
            insider_summary = f"\U0001f534 מכירה ({sells} עסקאות)"
        else:
            insider_summary = "\u26aa ללא פעילות פנים בולטת"

        massive_selling = sells >= 3 and sells > buys * 2

        return {
            "target_price":    target_price,
            "recommendation":  recom,
            "latest_news":     news_list,
            "insider_trading": insider_summary,
            "massive_selling": massive_selling,
            "error":           None,
        }

    except Exception as e:
        logger.debug("get_stock_context(%s) failed: %s", ticker, e)
        return {"error": str(e), "massive_selling": False}


def format_context_block(ctx: dict) -> str:
    """
    Format the stock context dict into a Hebrew Telegram Markdown block.
    Returns empty string if ctx is empty, has an error, or has no useful data.
    """
    if not ctx or ctx.get("error"):
        return ""

    tp  = ctx.get("target_price", "N/A")
    rec = ctx.get("recommendation", "N/A")
    if tp == "N/A" and rec == "N/A" and not ctx.get("latest_news"):
        return ""

    lines = ["\U0001f4f0 *פונדמנטלס וסנטימנט (FinViz):*"]

    if tp != "N/A" or rec != "N/A":
        rec_label = _recom_label(rec)
        lines.append(f"   \U0001f3af יעד אנליסטים: `${tp}` | דירוג: `{rec}` {rec_label}")

    insider = ctx.get("insider_trading", "")
    if insider:
        lines.append(f"   \U0001f465 פעילות פנים: {insider}")

    news = ctx.get("latest_news", [])
    if news:
        lines.append("   \U0001f5de\ufe0f כותרות אחרונות:")
        for item in news[:3]:
            lines.append(f"      \u2022 [{item['date']}] {item['title']}")

    return "\n".join(lines) if len(lines) > 1 else ""


def _recom_label(recom: str) -> str:
    """Convert numeric Finviz recommendation (1-5) to a short Hebrew label."""
    try:
        r = float(recom)
        if r <= 1.5:
            return "\U0001f7e2 קנייה חזקה"
        if r <= 2.5:
            return "\U0001f7e2 קנייה"
        if r <= 3.5:
            return "\U0001f7e1 החזק"
        if r <= 4.5:
            return "\U0001f534 מכירה"
        return "\U0001f534 מכירה חזקה"
    except Exception:
        return ""
