import logging
from datetime import date as _date
from datetime import datetime

import pytz
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}


class NewsScraper:
    def __init__(self):
        self.headers = _HEADERS

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def _fetch(self, url: str) -> requests.Response:
        resp = requests.get(url, headers=self.headers, timeout=15)
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Source-specific helpers
    # ------------------------------------------------------------------

    def _finviz_news(self, ticker: str, limit: int) -> list[dict]:
        """
        Fetch news from Finviz.
        Returns [] when the ticker is not tracked by Finviz (OTC/foreign)
        or on any network failure.
        """
        url = f"https://finviz.com/quote.ashx?t={ticker}&p=d"
        try:
            response = self._fetch(url)
        except Exception:
            logger.debug("Finviz fetch failed for %s", ticker)
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        news_table = soup.find(id="news-table")
        if not news_table:
            return []

        parsed_news: list[dict] = []
        last_date_str: str | None = None

        for idx, row in enumerate(news_table.find_all("tr")):
            if idx >= limit:
                break
            try:
                a_tag = row.find("a")
                if not a_tag:
                    continue

                headline = a_tag.text.strip()
                link = a_tag["href"]

                # Finviz only shows the date on the first row of each day;
                # subsequent rows only show the time.
                td_text = row.td.text.strip().split()
                if len(td_text) == 1:
                    time_str = td_text[0]
                    date_str = last_date_str
                else:
                    date_str = td_text[0]
                    time_str = td_text[1]
                    last_date_str = date_str

                if not date_str:
                    continue

                # Finviz uses "Today" for same-day rows; normalise to %b-%d-%y
                if date_str.lower() == "today":
                    date_str = _date.today().strftime("%b-%d-%y")

                news_dt = datetime.strptime(
                    f"{date_str} {time_str}", "%b-%d-%y %I:%M%p"
                ).replace(tzinfo=pytz.utc)

                parsed_news.append(
                    {
                        "ticker": ticker,
                        "headline": headline,
                        "url": link,
                        "published_at": news_dt,
                        "source": "Finviz",
                    }
                )
            except Exception:
                continue  # skip malformed rows

        return parsed_news

    def _yfinance_news(self, ticker: str, limit: int) -> list[dict]:
        """
        Fallback: fetch headlines via yfinance.

        Works for OTC stocks (CAMZF, WEICF, etc.) and foreign-listed tickers
        that Finviz doesn't track.  Yahoo Finance handles OTC symbols as plain
        tickers — the legacy .PK / .OB suffixes were retired in 2014 and are
        no longer needed.

        Supports both the legacy flat payload (yfinance <1.0) and the nested
        content dict introduced in yfinance ≥1.0.
        """
        try:
            items = yf.Ticker(ticker).news or []
            news: list[dict] = []
            for item in items[:limit]:
                content = item.get("content") or {}

                title = (
                    content.get("title")        # yfinance ≥1.0 (nested)
                    or item.get("title")         # yfinance <1.0 (flat)
                    or item.get("headline", "")  # legacy alias
                )
                if not title:
                    continue

                # Parse publish timestamp — could be an ISO string or a Unix int
                pub_dt: datetime | None = None
                raw_ts = content.get("pubDate") or item.get("providerPublishTime")
                if isinstance(raw_ts, int):
                    pub_dt = datetime.fromtimestamp(raw_ts, tz=pytz.utc)
                elif isinstance(raw_ts, str):
                    try:
                        pub_dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                url = (
                    item.get("link")
                    or content.get("canonicalUrl", {}).get("url", "")
                )

                news.append(
                    {
                        "ticker": ticker,
                        "headline": title.strip(),
                        "url": url,
                        "published_at": pub_dt or datetime.now(pytz.utc),
                        "source": "yfinance",
                    }
                )
            return news
        except Exception:
            logger.debug("yfinance news fetch failed for %s", ticker, exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_stock_news(self, ticker: str, limit: int = 20) -> list[dict]:
        """
        Returns up to `limit` recent news items for `ticker`.

        Strategy:
          1. Finviz  — fast, structured dates; covers NYSE / NASDAQ
          2. yfinance — fallback; covers OTC, foreign, and anything Yahoo tracks
          3. Both empty → quiet debug log, return []

        Each item: {ticker, headline, url, published_at, source}
        """
        # 1. Finviz (primary)
        news = self._finviz_news(ticker, limit)
        if news:
            logger.debug("Fetched %d news items for %s (Finviz)", len(news), ticker)
            return news

        # 2. yfinance (fallback for OTC / foreign)
        news = self._yfinance_news(ticker, limit)
        if news:
            logger.debug(
                "Fetched %d news items for %s (yfinance fallback)", len(news), ticker
            )
            return news

        # 3. Both failed — quiet skip, no loud warning
        logger.debug("No news found for %s (Finviz + yfinance both returned nothing)", ticker)
        return []

    # Backward-compatible alias used by existing callers
    def get_stock_data(self, ticker: str, limit: int = 20):
        """Legacy wrapper. Returns ({}, news_list) for backward compatibility."""
        return {}, self.get_stock_news(ticker, limit=limit)
