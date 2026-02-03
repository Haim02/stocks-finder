# from tradingview_screener import Query, Column
# import pandas as pd

# class ScreenerService:
#     @staticmethod
#     def get_candidates():
#         print("🔍 Scanning TradingView for candidates (Real-time)...")

#         try:
#             # 1. הגדרת השאילתה
#             q = Query().set_markets('america')

#             # 2. בחירה מפורשת של העמודות
#             q.select('name', 'close', 'volume', 'market_cap_basic')

#             # 3. הסינונים (כאן ה-WHERE שהיה חסר לך!)
#             q.where(
#                 Column('close') > 2.0,                     # סינון קריטי: רק מניות מעל 2 דולר
#                 Column('close') > Column('SMA200'),        # מניות במגמת עליה בלבד
#                 Column('relative_volume_10d_calc') > 1.2,  # ווליום חריג
#                 Column('type') == 'stock',                 # רק מניות (בלי תעודות סל)
#                 Column('average_volume_10d_calc') > 500000 # נזילות גבוהה
#             )

#             # מיון: אנחנו רוצים את אלו שזזו הכי חזק היום
#             q.order_by('change', ascending=False)
#             q.limit(30)

#             # 4. קבלת נתונים
#             response = q.get_scanner_data()

#             if not response or len(response) < 2:
#                 print("⚠️ No results returned.")
#                 return []

#             rows = response[1]
#             tickers = []

#             # --- זיהוי פורמט (DataFrame או List) ---
#             if hasattr(rows, 'columns') and hasattr(rows, 'iloc'):
#                 # מקרה א': קיבלנו טבלה של פנדס
#                 if 'name' in rows.columns:
#                     tickers = rows['name'].tolist()
#                 elif 'ticker' in rows.columns:
#                     tickers = rows['ticker'].tolist()
#             else:
#                 # מקרה ב': קיבלנו רשימה רגילה
#                 for row in rows:
#                     ticker = None
#                     if isinstance(row, dict):
#                         ticker = row.get('name')
#                     elif hasattr(row, 'name'):
#                         ticker = row.name
#                     elif isinstance(row, list) and len(row) > 0:
#                         ticker = row[0]

#                     if ticker:
#                         tickers.append(ticker)

#             # --- ניקוי סופי ---
#             clean_tickers = []
#             for t in tickers:
#                 if isinstance(t, str):
#                     # מנקה זבל כמו "NASDAQ:AAPL" -> "AAPL"
#                     clean_t = t.split(":")[-1].strip()
#                     # מוודא שזה לא כותרת
#                     if clean_t.lower() not in ['name', 'ticker', 'close', 'volume', 'n/a']:
#                         clean_tickers.append(clean_t)

#             # הסרת כפילויות
#             final_tickers = list(set(clean_tickers))

#             print(f"✅ Found {len(final_tickers)} valid stocks (> $2): {final_tickers}")
#             return final_tickers

#         except Exception as e:
#             print(f"❌ Error in Screener Logic: {e}")
#             return []




# from tradingview_screener import Query, Column
# import pandas as pd

# class ScreenerService:
#     @staticmethod
#     def get_candidates():
#         print("🔍 Scanning TradingView for Early Breakout candidates (High Relative Vol)...")

#         try:
#             q = Query().set_markets('america')

#             q.select('name', 'close', 'volume', 'market_cap_basic')

#             q.where(
#                 Column('close') > 5.0,                         # סינון מניות זבל (מעל 5$)
#                 Column('close') > Column('SMA200'),            # מגמת עליה ראשית (חובה)
#                 Column('average_volume_10d_calc') > 750000,    # נזילות גבוהה מאוד
#                 Column('relative_volume_10d_calc') > 1.2,      # ווליום גבוה ב-20% מהרגיל (סימן לכניסת כסף)
#                 Column('type') == 'stock'
#             )

#             # שינוי קריטי: מיון לפי ווליום יחסי במקום לפי אחוז שינוי!
#             # זה מביא מניות שמתבשל בהן מהלך, גם אם הן עוד לא טסו 10%
#             q.order_by('relative_volume_10d_calc', ascending=False)
#             q.limit(35)

#             response = q.get_scanner_data()

#             if not response or len(response) < 2:
#                 print("⚠️ No results returned.")
#                 return []

#             rows = response[1]
#             tickers = []

#             if hasattr(rows, 'columns') and hasattr(rows, 'iloc'):
#                 if 'name' in rows.columns:
#                     tickers = rows['name'].tolist()
#                 elif 'ticker' in rows.columns:
#                     tickers = rows['ticker'].tolist()
#             else:
#                 for row in rows:
#                     ticker = None
#                     if isinstance(row, dict):
#                         ticker = row.get('name')
#                     elif hasattr(row, 'name'):
#                         ticker = row.name
#                     elif isinstance(row, list) and len(row) > 0:
#                         ticker = row[0]

#                     if ticker:
#                         tickers.append(ticker)

#             # ניקוי
#             clean_tickers = []
#             for t in tickers:
#                 if isinstance(t, str):
#                     clean_t = t.split(":")[-1].strip()
#                     if clean_t.lower() not in ['name', 'ticker', 'close', 'volume', 'n/a']:
#                         clean_tickers.append(clean_t)

#             final_tickers = list(set(clean_tickers))
#             print(f"✅ Found {len(final_tickers)} potential early-movers: {final_tickers}")
#             return final_tickers

#         except Exception as e:
#             print(f"❌ Error in Screener Logic: {e}")
#             return []


# import requests
# from bs4 import BeautifulSoup

# class ScreenerService:
#     @staticmethod
#     def get_candidates_from_url(finviz_url):
#         """
#         מקבל URL של מסך תוצאות ב-Finviz ומחזיר רשימת טיקרים.
#         """
#         headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
#         tickers = []

#         try:
#             print(f"🌍 Fetching candidates from Finviz...")
#             response = requests.get(finviz_url, headers=headers)
#             soup = BeautifulSoup(response.content, 'html.parser')

#             # ב-Finviz הטיקרים נמצאים בתוך לינקים עם Class ספציפי
#             # הערה: הקלאס יכול להשתנות, כרגע זה screener-link-primary או דומה
#             links = soup.select('a.screener-link-primary')

#             for link in links:
#                 tickers.append(link.text.strip())

#             unique_tickers = list(set(tickers))
#             print(f"✅ Found {len(unique_tickers)} candidates.")
#             return unique_tickers

#         except Exception as e:
#             print(f"❌ Error fetching screener data: {e}")
#             return []


# import requests
# from bs4 import BeautifulSoup
# import time
# import random

# class ScreenerService:
#     @staticmethod
#     def get_candidates_from_url(finviz_url):
#         """
#         מושך טיקרים מ-Finviz.
#         תיקון: הסרנו את Accept-Encoding כדי לקבל טקסט קריא ולא דחוס.
#         """
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.5',
#             'Connection': 'keep-alive',
#             'Upgrade-Insecure-Requests': '1',
#             # מחקנו את שורת ה-Accept-Encoding כדי למנוע את הג'יבריש
#         }

#         tickers = []

#         try:
#             print(f"🌍 Fetching candidates from Finviz...")

#             # השהייה קצרה
#             time.sleep(random.uniform(1, 2))

#             response = requests.get(finviz_url, headers=headers)

#             # וידוא קידוד טקסט תקין
#             response.encoding = 'utf-8'

#             if response.status_code != 200:
#                 print(f"❌ Blocked/Error. Status: {response.status_code}")
#                 # רשימת חירום במקרה של חסימה, כדי שתראה שהמערכת עובדת
#                 return ["NVDA", "TSLA", "AMD"]

#             soup = BeautifulSoup(response.text, 'html.parser')

#             # ניסיון למצוא את הטיקרים ב-2 סוגי הלינקים ש-Finviz משתמש בהם
#             links = soup.select('a.screener-link-primary')
#             if not links:
#                 links = soup.select('a.screener-link')

#             for link in links:
#                 txt = link.text.strip()
#                 # בדיקת תקינות: טיקר הוא באותיות גדולות, קצר, וללא מספרים
#                 if txt.isupper() and len(txt) <= 5 and txt.isalpha():
#                     tickers.append(txt)

#             unique_tickers = list(set(tickers))

#             if not unique_tickers:
#                 print("⚠️ Warning: No tickers found in HTML. Finviz structure might have changed.")
#                 # החזרת רשימת ברירת מחדל כדי לא לעצור את התהליך
#                 return ["TSLA", "NVDA", "PLTR", "SOFI", "MARA"]

#             print(f"✅ Found {len(unique_tickers)} candidates: {unique_tickers}")
#             return unique_tickers

#         except Exception as e:
#             print(f"❌ Error fetching screener data: {e}")
#             return ["TSLA", "NVDA"] # Fallback



# import cloudscraper
# from bs4 import BeautifulSoup
# import time
# import random
# import re

# class ScreenerService:
#     @staticmethod
#     def get_candidates_from_url(finviz_url):
#         """
#         מושך טיקרים מ-Finviz באמצעות cloudscraper וזיהוי קישורים חכם (Regex).
#         """
#         scraper = cloudscraper.create_scraper(
#             browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
#         )

#         tickers = []

#         try:
#             print(f"🌍 Fetching candidates from Finviz (Regex Method)...")
#             response = scraper.get(finviz_url)

#             if response.status_code != 200:
#                 print(f"❌ Blocked/Error. Status: {response.status_code}")
#                 return ["TSLA", "NVDA", "AMD"]

#             soup = BeautifulSoup(response.text, 'html.parser')

#             # --- השינוי הגדול: חיפוש לפי מבנה הקישור ולא לפי עיצוב ---
#             # אנחנו מחפשים כל לינק שמתחיל ב- "quote.ashx?t="
#             # זה עובד תמיד, לא משנה אם Finviz משנים את העיצוב
#             all_links = soup.find_all('a', href=True)

#             for link in all_links:
#                 href = link['href']

#                 # בדיקה אם הלינק מוביל למניה
#                 if "quote.ashx?t=" in href:
#                     # חילוץ הטיקר מהלינק או מהטקסט
#                     # דוגמה ללינק: quote.ashx?t=AAPL&ty=c...
#                     # אנחנו רוצים רק את ה-AAPL

#                     # ננסה לקחת את הטקסט של הלינק קודם (בדרך כלל זה הטיקר)
#                     ticker_text = link.text.strip()

#                     # וידוא שזה נראה כמו טיקר (אותיות גדולות, קצר)
#                     if ticker_text.isupper() and len(ticker_text) <= 5 and ticker_text.isalpha():
#                          tickers.append(ticker_text)
#                     else:
#                         # ניסיון חילוץ מתוך ה-URL אם הטקסט לא ברור
#                         match = re.search(r't=([A-Z]+)', href)
#                         if match:
#                             tickers.append(match.group(1))

#             # הסרת כפילויות (כי לפעמים יש כמה לינקים לאותה מניה בדף)
#             unique_tickers = list(set(tickers))

#             if not unique_tickers:
#                 print("⚠️ Warning: No tickers found. Check if your filter yields 0 results.")
#                 print(f"Debug Title: {soup.title.string if soup.title else 'No Title'}")
#                 return ["TSLA", "NVDA"] # Fallback

#             print(f"✅ Found {len(unique_tickers)} candidates: {unique_tickers}")
#             return unique_tickers

#         except Exception as e:
#             print(f"❌ Error scraping: {e}")
#             return ["TSLA", "NVDA"]


import cloudscraper
from bs4 import BeautifulSoup
import re

class ScreenerService:
    @staticmethod
    def get_candidates_from_url(finviz_url):
        """
        מושך טיקרים מ-Finviz באמצעות cloudscraper וזיהוי קישורים חכם (Regex).
        גרסה נקייה - ללא מניות גיבוי.
        """
        # הגדרת דפדפן מזויף לעקיפת חסימות
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )

        tickers = []

        try:
            print(f"🌍 Fetching candidates from Finviz...")
            response = scraper.get(finviz_url)

            if response.status_code != 200:
                print(f"❌ Blocked/Error. Status: {response.status_code}")
                return [] # אין תוצאות

            soup = BeautifulSoup(response.text, 'html.parser')

            # חיפוש כל הלינקים שמובילים לעמוד מניה (quote.ashx?t=...)
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                href = link['href']

                if "quote.ashx?t=" in href:
                    ticker_text = link.text.strip()

                    # וידוא שזה אכן טיקר תקין (אותיות גדולות, קצר)
                    if ticker_text.isupper() and len(ticker_text) <= 5 and ticker_text.isalpha():
                         tickers.append(ticker_text)
                    else:
                        # גיבוי: חילוץ הטיקר מתוך ה-URL עצמו אם הטקסט לא ברור
                        match = re.search(r't=([A-Z]+)', href)
                        if match:
                            tickers.append(match.group(1))

            unique_tickers = list(set(tickers))

            if not unique_tickers:
                print("⚠️ No tickers found matching your criteria.")
                return []

            print(f"✅ Found {len(unique_tickers)} candidates: {unique_tickers}")
            return unique_tickers

        except Exception as e:
            print(f"❌ Error scraping: {e}")
            return []