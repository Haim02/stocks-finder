import logging
import os
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

# Dedicated Chrome profile so the bot doesn't conflict with your regular browser.
_BOT_PROFILE_PATH = r"C:\ChromeBotProfile"


class TradingViewService:
    @staticmethod
    def get_candidates_from_url(tradingview_url: str, limit: int = 500) -> list[str]:
        """
        Scrapes tickers from a TradingView screener URL using Selenium.

        On first run the bot opens Chrome so you can log in to TradingView,
        then press Enter to continue.  Subsequent runs reuse the saved session.

        Returns a list of ticker strings (empty on failure).
        """
        logger.info("Launching TradingView Scanner (Selenium)...")

        os.makedirs(_BOT_PROFILE_PATH, exist_ok=True)

        options = Options()
        options.add_argument(f"user-data-dir={_BOT_PROFILE_PATH}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)

            logger.info("Navigating to %s", tradingview_url)
            driver.get(tradingview_url)

            print("\n" + "=" * 55)
            print("Browser opened. If you are not logged in to TradingView,")
            print("please log in now, then return here and press Enter.")
            print("=" * 55 + "\n")
            input("Press Enter when ready...")

            logger.info("Refreshing page to load screener data...")
            driver.get(tradingview_url)
            time.sleep(5)

            # Scroll down until no new content loads (infinite scroll).
            logger.info("Scrolling to load all tickers...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(30):  # safety cap
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            soup = BeautifulSoup(driver.page_source, "html.parser")

            tickers: list[str] = []
            seen: set[str] = set()

            # Primary extraction: links with TradingView's screener symbol class.
            for el in soup.find_all("a", class_="tv-screener__symbol"):
                t = el.text.strip()
                if t and t not in seen:
                    tickers.append(t)
                    seen.add(t)

            # Fallback: any uppercase short link text pointing to symbol pages.
            if not tickers:
                logger.warning("Primary extraction empty — trying fallback method.")
                for link in soup.find_all("a"):
                    txt = link.text.strip()
                    href = link.get("href", "")
                    if txt.isupper() and 2 <= len(txt) <= 5 and txt.isalpha():
                        if ("symbols" in href or "quote" in href) and txt not in seen:
                            tickers.append(txt)
                            seen.add(txt)

            result = tickers[:limit]
            logger.info("TradingView Scraper: collected %d tickers.", len(result))
            return result

        except Exception:
            logger.exception("Selenium error during TradingView scrape")
            return []

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
