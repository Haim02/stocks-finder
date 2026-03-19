"""
Finviz scanner helper for the Options module.

Provides pre-configured bullish and bearish momentum scans that feed
the daily options pipeline.  Thin wrapper around ScreenerService so
we keep all Finviz scraping logic in one place.
"""

import logging

from app.services.screener_service import ScreenerService

logger = logging.getLogger(__name__)

_BASE = "https://finviz.com/screener.ashx?v=211&ft=4"

# Price above all major SMAs, positive daily performance, high relative volume
BULLISH_URL = (
    f"{_BASE}"
    "&f=ta_perf_curr_up,ta_sma20_pa,ta_sma50_pa,ta_sma200_pa,sh_avgvol_o500"
)

# Price below all major SMAs, negative daily performance, high relative volume
BEARISH_URL = (
    f"{_BASE}"
    "&f=ta_perf_curr_dn,ta_sma20_pb,ta_sma50_pb,ta_sma200_pb,sh_avgvol_o500"
)


class FinvizService:
    """Momentum scans used to seed the options pipeline."""

    @staticmethod
    def get_bullish_tickers(n: int = 20) -> list[str]:
        """Returns up to `n` bullish momentum tickers from Finviz."""
        logger.info("Finviz bullish scan (target=%d)...", n)
        tickers = ScreenerService.get_candidates_from_url(BULLISH_URL, limit=n)
        logger.info("Bullish scan: %d tickers found.", len(tickers))
        return tickers

    @staticmethod
    def get_bearish_tickers(n: int = 20) -> list[str]:
        """Returns up to `n` bearish momentum tickers from Finviz."""
        logger.info("Finviz bearish scan (target=%d)...", n)
        tickers = ScreenerService.get_candidates_from_url(BEARISH_URL, limit=n)
        logger.info("Bearish scan: %d tickers found.", len(tickers))
        return tickers
