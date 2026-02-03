import requests
from bs4 import BeautifulSoup
import time

class NewsScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def get_stock_data(self, ticker):
        """
        נכנס לעמוד המניה הספציפי ב-Finviz ושולף:
        1. טבלת נתונים (Fundamentals)
        2. חדשות אחרונות
        """
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 1. חילוץ נתונים פונדמנטליים מהטבלה הגדולה
            stats = {}
            rows = soup.find_all('tr', class_='table-quote-row')
            for row in rows:
                cols = row.find_all('td')
                for i in range(0, len(cols), 2):
                    key = cols[i].text.strip()
                    val = cols[i+1].text.strip()
                    stats[key] = val

            # 2. חילוץ חדשות (10 האחרונות)
            news_items = []
            news_table = soup.find(id='news-table')
            if news_table:
                for row in news_table.find_all('tr')[:10]:
                    if row.a:
                        news_items.append({
                            'headline': row.a.text,
                            'url': row.a['href']
                        })

            return stats, news_items

        except Exception as e:
            print(f"⚠️ Error scraping {ticker}: {e}")
            return {}, []