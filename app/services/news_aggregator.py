# import feedparser
# from datetime import datetime, timedelta
# from dateutil import parser
# import pytz
# import re

# class NewsAggregator:
#     def __init__(self):
#         # רשימת המקורות הכי חזקים (RSS רשמיים)
#         self.feeds = {
#             "GlobeNewswire": "https://www.globenewswire.com/RssFeed/subject/code/MERGER-ACQUISITION-NEWS?include10K=False",
#             "PR Newswire": "https://www.prnewswire.com/rss/news/all-news-releases",
#             "Benzinga": "https://feeds.benzinga.com/benzinga/news",
#             "FDA Updates": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
#             "Yahoo Finance": "https://finance.yahoo.com/news/rssindex"
#         }

#         # מילות מפתח לסינון - נשמור רק מה שבאמת חשוב
#         self.keywords = [
#             "fda", "approval", "cleared", "phase 3", "phase 2", # ביוטק
#             "merger", "acquisition", "agreement", "contract", "partnership", # עסקאות
#             "guidance", "upgrade", "buy rating", "patent", "awarded", "earnings" # זרזים
#         ]

#     def fetch_last_24h_news(self):
#         """מושך חדשות מכל המקורות מה-24 שעות האחרונות"""
#         print("🌍 Aggregating global market news (Last 24h)...")

#         news_items = []
#         utc_now = datetime.now(pytz.utc)
#         one_day_ago = utc_now - timedelta(days=1)

#         for source, url in self.feeds.items():
#             try:
#                 feed = feedparser.parse(url)

#                 for entry in feed.entries:
#                     # טיפול בתאריכים (המרה ל-UTC)
#                     try:
#                         if hasattr(entry, 'published'):
#                             pub_date = parser.parse(entry.published)
#                         elif hasattr(entry, 'updated'):
#                             pub_date = parser.parse(entry.updated)
#                         else:
#                             continue

#                         if pub_date.tzinfo is None:
#                             pub_date = pub_date.replace(tzinfo=pytz.utc)
#                         else:
#                             pub_date = pub_date.astimezone(pytz.utc)

#                         # סינון זמן: רק 24 שעות אחרונות
#                         if pub_date < one_day_ago:
#                             continue

#                         headline = entry.title
#                         link = entry.link

#                         # סינון תוכן: רק אם יש מילות מפתח מעניינות
#                         if self._is_relevant(headline):
#                             ticker = self._extract_ticker(headline) or "GENERAL"

#                             news_items.append({
#                                 "source": source,
#                                 "ticker": ticker,
#                                 "headline": headline,
#                                 "url": link,
#                                 "published_at": pub_date.strftime("%Y-%m-%d %H:%M"),
#                                 "raw_date": pub_date # לשימוש פנימי ומיון
#                             })

#                     except Exception as e:
#                         continue
#             except Exception as e:
#                 print(f"❌ Error reading feed {source}: {e}")

#         # מיון החדשות מהחדש לישן
#         news_items.sort(key=lambda x: x['raw_date'], reverse=True)
#         print(f"✅ Found {len(news_items)} important news items.")
#         return news_items

#     def _is_relevant(self, text):
#         text_lower = text.lower()
#         for kw in self.keywords:
#             if kw in text_lower:
#                 return True
#         return False

#     def _extract_ticker(self, text):
#         """מנסה למצוא טיקר בתוך סוגריים, למשל (AAPL)"""
#         match = re.search(r'\(([A-Z]{2,5})\)', text)
#         if match:
#             return match.group(1)
#         return None



import feedparser
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import re

class NewsAggregator:
    def __init__(self):
        # מקורות מידע חזקים לביוטק והודעות לעיתונות
        self.feeds = {
            "GlobeNewswire": "https://www.globenewswire.com/RssFeed/subject/code/MERGER-ACQUISITION-NEWS?include10K=False",
            "PR Newswire": "https://www.prnewswire.com/rss/news/all-news-releases",
            "Benzinga": "https://feeds.benzinga.com/benzinga/news",
            "FDA Updates": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
            "Yahoo Finance": "https://finance.yahoo.com/news/rssindex"
        }

        # מילות מפתח כלליות לחדשות שוק
        self.general_keywords = [
            "merger", "acquisition", "agreement", "contract", "partnership",
            "guidance", "upgrade", "earnings"
        ]

        # מילות מפתח ספציפיות ל"צייד הביוטק"
        self.biotech_keywords = [
            "fda approval", "fda approved", "cleared by fda", # אישורים
            "phase 3", "phase iii", "phase 4", "phase iv",    # שלבים מתקדמים
            "primary endpoint", "clinical trial results",     # תוצאות ניסוי
            "fast track designation", "orphan drug",          # רגולציה חיובית
            "pdufa"                                           # תאריך יעד לאישור
        ]

    def fetch_last_24h_news(self):
        """מושך חדשות כלליות (כמו שיש לך היום)"""
        return self._scan_feeds(mode="general")

    def find_biotech_opportunities(self):
        """
        פונקציה חדשה: מחזירה רשימה של טיקרים (סימולים) של מניות ביוטק
        שיש להן חדשות מרעישות מהיממה האחרונה.
        """
        print("🧬 Scanning for Biotech/FDA opportunities...")
        news_items = self._scan_feeds(mode="biotech")

        biotech_tickers = []
        for item in news_items:
            # אם מצאנו טיקר בתוך החדשה - זו הזדמנות!
            if item['ticker'] and item['ticker'] != "GENERAL":
                biotech_tickers.append(item['ticker'])

        # הסרת כפילויות (למשל אותה מניה הופיעה ב-2 אתרים)
        unique_tickers = list(set(biotech_tickers))
        if unique_tickers:
            print(f"🧬 Found {len(unique_tickers)} Biotech stocks with major news: {unique_tickers}")
        return unique_tickers

    def _scan_feeds(self, mode="general"):
        """פונקציה פנימית לסריקת הפידים לפי מצב"""
        news_items = []
        utc_now = datetime.now(pytz.utc)
        one_day_ago = utc_now - timedelta(days=1)

        # הגדרת אזורי זמן לתיקון האזהרה
        tzinfos = {
            "EST": -18000, "EDT": -14400, "CST": -21600, "CDT": -18000,
            "PST": -28800, "PDT": -25200
        }

        keywords = self.biotech_keywords if mode == "biotech" else self.general_keywords

        for source, url in self.feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    try:
                        # זיהוי תאריך
                        if hasattr(entry, 'published'):
                            pub_date = parser.parse(entry.published, tzinfos=tzinfos)
                        elif hasattr(entry, 'updated'):
                            pub_date = parser.parse(entry.updated, tzinfos=tzinfos)
                        else:
                            continue

                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=pytz.utc)
                        else:
                            pub_date = pub_date.astimezone(pytz.utc)

                        if pub_date < one_day_ago:
                            continue

                        headline = entry.title
                        link = entry.link

                        # בדיקת מילות מפתח
                        if self._is_relevant(headline, keywords):
                            ticker = self._extract_ticker(headline) or "GENERAL"

                            news_items.append({
                                "source": source,
                                "ticker": ticker,
                                "headline": headline,
                                "url": link,
                                "published_at": pub_date.strftime("%Y-%m-%d %H:%M"),
                                "raw_date": pub_date
                            })

                    except Exception:
                        continue
            except Exception:
                pass

        news_items.sort(key=lambda x: x['raw_date'], reverse=True)
        return news_items

    def _is_relevant(self, text, keywords):
        text_lower = text.lower()
        for kw in keywords:
            if kw in text_lower:
                return True
        return False

    def _extract_ticker(self, text):
        """
        מחלץ טיקרים מפורמטים נפוצים:
        (NASDAQ: AAPL), (NYSE: T), (AAPL)
        """
        # ניסיון 1: פורמט מלא (NASDAQ: XXXX)
        match = re.search(r'\((?:NASDAQ|NYSE|AMEX):\s?([A-Z]{2,5})\)', text, re.IGNORECASE)
        if match:
            return match.group(1)

        # ניסיון 2: פורמט קצר (XXXX) - אבל רק אותיות גדולות ומקפים
        # נזהר לא לתפוס מילים רגילות בסוגריים כמו (Phase 3)
        match_simple = re.search(r'\s\(([A-Z]{2,5})\)', text)
        if match_simple:
            # סינון רעשים: מוודא שזה לא מילה נפוצה
            candidate = match_simple.group(1)
            if candidate not in ["FDA", "USA", "CEO", "CFO", "YOY", "QOQ", "USD"]:
                return candidate

        return None