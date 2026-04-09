"""
Index Universe — fetch S&P 500 and Nasdaq 100 constituents.
Used by /strategies to ensure tickers are liquid, well-known stocks.

Sources (in priority order):
1. Wikipedia (free, always works) — S&P 500 and Nasdaq 100 tables
2. Hardcoded curated list (final fallback)
"""

import logging
import random
from datetime import date

logger = logging.getLogger(__name__)

# ── Curated fallback lists (top liquid S&P 500 + Nasdaq stocks) ──────────────
SP500_CORE = [
    # Tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD", "INTC", "CRM",
    "ADBE", "ORCL", "QCOM", "TXN", "AVGO", "MU", "AMAT", "LRCX", "KLAC", "MRVL",
    # Finance
    "JPM", "BAC", "GS", "MS", "WFC", "C", "AXP", "V", "MA", "BLK",
    # Healthcare
    "JNJ", "PFE", "ABBV", "MRK", "LLY", "AMGN", "BIIB", "GILD", "REGN", "BMY",
    # Consumer
    "HD", "MCD", "NKE", "SBUX", "TGT", "WMT", "COST", "PG", "KO", "PEP",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "MPC", "VLO", "PSX", "HAL",
    # Industrial
    "BA", "CAT", "DE", "HON", "GE", "MMM", "RTX", "LMT", "NOC", "GD",
    # Communication
    "DIS", "NFLX", "CMCSA", "T", "VZ", "PARA", "WBD", "SNAP", "PINS", "RBLX",
]

NASDAQ100_CORE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "ASML",
    "NFLX", "AMD", "AZN", "QCOM", "LIN", "CSCO", "ADBE", "TXN", "INTU", "AMGN",
    "MU", "ISRG", "BKNG", "AMAT", "NOW", "PANW", "REGN", "ADI", "LRCX", "KLAC",
    "MRVL", "SNPS", "CDNS", "CRWD", "FTNT", "MELI", "ABNB", "DXCM", "WDAY", "NXPI",
    "ORLY", "PYPL", "PCAR", "CTAS", "FAST", "IDXX", "TEAM", "ZS", "OKTA",
    "DDOG", "SNOW", "PLTR", "COIN", "HOOD", "SOFI",
]


def _wiki_tables(url: str) -> list:
    """Fetch Wikipedia tables with a browser User-Agent to avoid 403."""
    import requests
    import pandas as pd
    from io import StringIO
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return pd.read_html(StringIO(resp.text))


def get_sp500_tickers() -> list[str]:
    """
    Fetch current S&P 500 constituents from Wikipedia.
    Returns list of ticker symbols.
    """
    try:
        tables = _wiki_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df     = tables[0]
        col    = "Symbol" if "Symbol" in df.columns else df.columns[0]
        tickers = df[col].str.replace(".", "-", regex=False).tolist()
        result  = [t.strip().upper() for t in tickers if isinstance(t, str) and t.strip()]
        logger.info("[IndexUniverse] S&P 500: %d tickers from Wikipedia", len(result))
        return result
    except Exception as e:
        logger.warning("[IndexUniverse] Wikipedia S&P 500 failed: %s", e)
        return SP500_CORE.copy()


def get_nasdaq100_tickers() -> list[str]:
    """
    Fetch current Nasdaq 100 constituents from Wikipedia.
    Returns list of ticker symbols.
    """
    try:
        tables = _wiki_tables("https://en.wikipedia.org/wiki/Nasdaq-100")
        for df in tables:
            cols = [str(c).lower() for c in df.columns]
            if "ticker" in cols or "symbol" in cols:
                col     = next(c for c in df.columns if str(c).lower() in ("ticker", "symbol"))
                tickers = df[col].dropna().tolist()
                result  = [str(t).strip().upper() for t in tickers if str(t).strip()]
                logger.info("[IndexUniverse] Nasdaq 100: %d tickers from Wikipedia", len(result))
                return result
    except Exception as e:
        logger.warning("[IndexUniverse] Wikipedia Nasdaq 100 failed: %s", e)
    return NASDAQ100_CORE.copy()


def get_combined_universe(
    include_sp500:  bool = True,
    include_nasdaq: bool = True,
    shuffle:        bool = True,
) -> list[str]:
    """
    Returns combined unique list of S&P 500 + Nasdaq 100 tickers.
    """
    tickers: set[str] = set()
    if include_sp500:
        tickers.update(get_sp500_tickers())
    if include_nasdaq:
        tickers.update(get_nasdaq100_tickers())

    result = list(tickers)
    if shuffle:
        random.shuffle(result)
    return result


def get_daily_candidates(
    n:              int  = 30,
    include_sp500:  bool = True,
    include_nasdaq: bool = True,
) -> list[str]:
    """
    Returns N tickers from the index universe, rotated daily so
    every run surfaces different stocks.

    Rotation: uses day-of-year as an offset into the sorted universe,
    then shuffles within the daily slice for variety.
    """
    # Use a stable (sorted) universe for reproducible daily rotation
    universe = get_combined_universe(
        include_sp500=include_sp500,
        include_nasdaq=include_nasdaq,
        shuffle=False,
    )
    universe.sort()   # stable order before rotating

    if not universe:
        fallback = SP500_CORE.copy()
        random.shuffle(fallback)
        return fallback[:n]

    # Day-of-year offset — different slice every day, wraps around
    day_num = date.today().timetuple().tm_yday
    pool    = max(len(universe) - n, 1)
    start   = (day_num * n) % pool
    slice_  = universe[start: start + n]

    # Wrap around if the slice is shorter than n
    if len(slice_) < n:
        slice_ = slice_ + universe[:n - len(slice_)]

    random.shuffle(slice_)
    return slice_[:n]


def classify_ticker_trend(ticker: str) -> str:
    """
    Quick trend classification using yfinance price vs MAs.
    Returns: "bullish" | "bearish" | "neutral"
    """
    try:
        import yfinance as yf
        hist  = yf.Ticker(ticker).history(period="3mo")
        if len(hist) < 50:
            return "neutral"
        close = hist["Close"]
        price = float(close.iloc[-1])
        ma20  = float(close.rolling(20).mean().iloc[-1])
        ma50  = float(close.rolling(50).mean().iloc[-1])
        if price > ma20 > ma50:
            return "bullish"
        elif price < ma20 < ma50:
            return "bearish"
        return "neutral"
    except Exception:
        return "neutral"
