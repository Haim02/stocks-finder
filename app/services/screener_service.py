import logging
import random
import re
import time

import cloudscraper
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_SCRAPER = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "desktop": True}
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_page(url: str):
    """Fetch a single Finviz screener page with anti-bot headers."""
    resp = _SCRAPER.get(url, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}")
    return resp


class ScreenerService:
    @staticmethod
    def get_candidates_from_url(finviz_url: str, limit: int = 150) -> list[str]:
        """
        Scrapes tickers from a Finviz screener URL with multi-page support.
        limit: max tickers to return (default 150; keep ≤200 to avoid blocks).
        Returns [] on failure.
        """
        found_tickers: set[str] = set()
        page = 1

        logger.info("Fetching up to %d candidates from Finviz...", limit)

        while len(found_tickers) < limit:
            offset = (page - 1) * 20 + 1
            page_url = f"{finviz_url}&r={offset}"

            try:
                response = _fetch_page(page_url)
            except Exception:
                logger.warning("Screener fetch failed on page %d, stopping.", page)
                break

            soup = BeautifulSoup(response.text, "html.parser")
            tickers_on_page = 0

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "quote.ashx?t=" not in href:
                    continue

                ticker_text = link.text.strip()
                if ticker_text.isupper() and 1 <= len(ticker_text) <= 5 and ticker_text.isalpha():
                    ticker_to_add = ticker_text
                else:
                    m = re.search(r"t=([A-Z]{1,5})", href)
                    ticker_to_add = m.group(1) if m else None

                if ticker_to_add and ticker_to_add not in found_tickers:
                    found_tickers.add(ticker_to_add)
                    tickers_on_page += 1

            logger.info(
                "Page %d: +%d tickers (total %d)", page, tickers_on_page, len(found_tickers)
            )

            if tickers_on_page == 0:
                break  # no more results

            if len(found_tickers) >= limit:
                break

            time.sleep(random.uniform(1.5, 3.0))
            page += 1

        result = list(found_tickers)[:limit]
        if not result:
            logger.warning("No tickers found matching the Finviz screener criteria.")
        else:
            logger.info("Collected %d unique tickers from Finviz.", len(result))
        return result
