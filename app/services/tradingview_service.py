import logging
import os
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

# ── Chrome profile path — platform-aware ──────────────────────────────────────
# On Windows (local dev): use a dedicated profile so the bot doesn't conflict
# with your regular browser session and TradingView login is preserved.
# On Linux / Railway: use a temp directory inside the project (no persistence,
# but the bot runs headless so no login prompt is shown).
_IS_HEADLESS = os.getenv("CHROME_HEADLESS", "0") == "1"

if os.name == "nt":  # Windows
    _BOT_PROFILE_PATH = r"C:\ChromeBotProfile"
else:                # Linux (Railway, Docker, VPS)
    _BOT_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chrome_profile")


class TradingViewService:
    @staticmethod
    def get_candidates_from_url(tradingview_url: str, limit: int = 500) -> list[str]:
        """
        Scrapes tickers from a TradingView screener URL using Selenium.

        Local (interactive) mode:
            Opens Chrome with a saved profile. On first run you can log in to
            TradingView, then press Enter to continue. Subsequent runs reuse the
            saved session.

        Headless mode (CHROME_HEADLESS=1 — Railway/Docker):
            Runs Chrome with no window. The TradingView login session cannot be
            set up interactively, so the scraper will return whatever is visible
            on the public screener page. If the page requires login it returns [].
            Use Finviz as the primary source in production (--source finviz or both).

        Returns a list of ticker strings (empty on failure).
        """
        logger.info("Launching TradingView Scanner (Selenium, headless=%s)...", _IS_HEADLESS)

        os.makedirs(_BOT_PROFILE_PATH, exist_ok=True)

        options = Options()
        options.add_argument(f"user-data-dir={_BOT_PROFILE_PATH}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")                  # required in containers
        options.add_argument("--disable-dev-shm-usage")       # prevents /dev/shm OOM crash
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if _IS_HEADLESS:
            options.add_argument("--headless=new")

        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)

            logger.info("Navigating to %s", tradingview_url)
            driver.get(tradingview_url)

            # Interactive login prompt — only shown when NOT headless
            if not _IS_HEADLESS:
                print("\n" + "=" * 55)
                print("Browser opened. If you are not logged in to TradingView,")
                print("please log in now, then return here and press Enter.")
                print("=" * 55 + "\n")
                input("Press Enter when ready...")

            logger.info("Refreshing page to load screener data...")
            driver.get(tradingview_url)
            time.sleep(5)

            # Scroll until no new content loads (infinite scroll)
            logger.info("Scrolling to load all tickers...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(30):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            soup = BeautifulSoup(driver.page_source, "html.parser")

            tickers: list[str] = []
            seen: set[str] = set()

            # Primary extraction: TradingView screener symbol links
            for el in soup.find_all("a", class_="tv-screener__symbol"):
                t = el.text.strip()
                if t and t not in seen:
                    tickers.append(t)
                    seen.add(t)

            # Fallback: any short uppercase link text on symbol pages
            if not tickers:
                logger.warning("Primary extraction empty — trying fallback method.")
                for link in soup.find_all("a"):
                    txt  = link.text.strip()
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
