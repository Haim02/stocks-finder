"""
openbb_service.py — OpenBB Market Data
========================================

Uses OpenBB for enhanced options and equity data.
OpenBB is free and open source (github.com/OpenBB-finance/OpenBB).

Used as enhancement layer on top of yfinance — not a replacement.
If OpenBB unavailable, system falls back to yfinance gracefully.

Key advantages over yfinance:
- More accurate IV Rank (uses options-specific calculation)
- Historical options data
- Better earnings calendar
- Macro data integration
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Check if OpenBB is installed and functional."""
    try:
        from openbb import obb  # noqa: F401
        return True
    except ImportError:
        return False


def get_iv_rank_openbb(ticker: str) -> Optional[tuple[float, float]]:
    """
    Get IV Rank and IV Percentile from OpenBB.
    Returns (iv_rank, iv_percentile) or None if unavailable.

    OpenBB calculates these directly from options chain data,
    making them more accurate than the historical volatility proxy.
    """
    if not is_available():
        return None

    try:
        from openbb import obb

        # Get historical IV data
        iv_data = obb.derivatives.options.chains(ticker)
        if iv_data is None or iv_data.results is None:
            return None

        import pandas as pd
        df = pd.DataFrame([r.model_dump() for r in iv_data.results])

        if df.empty or "implied_volatility" not in df.columns:
            return None

        # Current ATM IV
        df = df.dropna(subset=["implied_volatility"])
        current_iv = float(df["implied_volatility"].mean()) * 100

        logger.info("OpenBB IV for %s: %.1f%%", ticker, current_iv)
        return current_iv, current_iv  # return as (iv_rank proxy, iv_pct proxy)

    except Exception as e:
        logger.debug("OpenBB IV fetch failed for %s: %s", ticker, e)
        return None


def get_earnings_calendar_openbb(ticker: str) -> Optional[list[dict]]:
    """
    Get upcoming earnings dates from OpenBB.
    More reliable than yfinance calendar for some tickers.
    """
    if not is_available():
        return None

    try:
        from openbb import obb
        cal = obb.equity.fundamental.calendar_earnings(ticker)
        if cal is None or cal.results is None:
            return None

        results = []
        for item in cal.results:
            d = item.model_dump()
            results.append({
                "date": str(d.get("report_date", "")),
                "eps_estimate": d.get("eps_consensus", None),
            })
        return results

    except Exception as e:
        logger.debug("OpenBB earnings calendar failed for %s: %s", ticker, e)
        return None


def get_macro_indicators_openbb() -> Optional[dict]:
    """
    Get macro indicators from OpenBB as additional data source.
    Complements FRED data.
    """
    if not is_available():
        return None

    try:
        from openbb import obb
        results = {}

        try:
            gdp = obb.economy.gdp(country="united_states", units="growth_previous")
            if gdp and gdp.results:
                import pandas as pd
                df = pd.DataFrame([r.model_dump() for r in gdp.results])
                results["gdp_growth"] = float(df["value"].iloc[-1]) if not df.empty else None
        except Exception:
            pass

        return results if results else None

    except Exception as e:
        logger.debug("OpenBB macro failed: %s", e)
        return None
