import requests
import yfinance as yf
import pandas as pd
from app.core.config import settings
from datetime import datetime, timedelta

class DataFetcher:
    @staticmethod
    def get_stock_data(ticker):
        """
        מושך נתוני מחיר היסטוריים מ-Yahoo Finance.
        כולל הגנות מפני נתונים ריקים והמרת שמות עמודות.
        """
        try:
            stock = yf.Ticker(ticker)
            # משיכת נתונים לשנה האחרונה
            df = stock.history(period="1y", timeout=15)

            # בדיקה אם חזרו נתונים בכלל
            if df is None or df.empty or len(df) < 50:
                print(f"⚠️ No sufficient data for {ticker}")
                return None

            # תיקון שמות עמודות לאותיות קטנות (פותר את שגיאת 'close')
            df.columns = [col.lower() for col in df.columns]

            return df
        except Exception as e:
            print(f"❌ Error fetching price data for {ticker}: {e}")
            return None

    @staticmethod
    def get_finnhub_fundamentals(ticker):
        """
        מושך נתונים פונדמנטליים (מכפילים, צמיחה, חוב) מ-Finnhub.
        """
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={settings.FINNHUB_API_KEY}"
        try:
            response = requests.get(url, timeout=10)
            res = response.json()
            metrics = res.get('metric', {})

            return {
                "pe_ratio": metrics.get('peExclExtraTTM', 'N/A'),
                "ps_ratio": metrics.get('psTTM', 'N/A'),
                "revenue_growth_yoy": metrics.get('revenueGrowthQuarterlyYoy', 'N/A'),
                "debt_to_equity": metrics.get('totalDebt/totalEquityQuarterly', 'N/A'),
                "net_margin": metrics.get('netProfitMarginTTM', 'N/A'),
                "52_week_high": metrics.get('52WeekHigh', 'N/A')
            }
        except Exception as e:
            print(f"⚠️ Finnhub fundamentals error for {ticker}: {e}")
            return {}

    @staticmethod
    def get_finnhub_news(ticker):
        """
        מושך את 5 כותרות החדשות האחרונות מהשבוע האחרון דרך Finnhub.
        """
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={settings.FINNHUB_API_KEY}"
        try:
            response = requests.get(url, timeout=10)
            news = response.json()

            # מחזיר רק את הכותרות של 5 הידיעות הראשונות
            if isinstance(news, list):
                return [n['headline'] for n in news[:5]]
            return []
        except Exception as e:
            print(f"⚠️ Finnhub news error for {ticker}: {e}")
            return []

    @staticmethod
    def get_company_profile(ticker):
        """
        אופציונלי: מושך תיאור קצר על החברה (סקטור, תעשייה).
        """
        url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={settings.FINNHUB_API_KEY}"
        try:
            res = requests.get(url, timeout=10).json()
            return {
                "name": res.get('name', ticker),
                "industry": res.get('finnhubIndustry', 'N/A'),
                "market_cap": res.get('marketCapitalization', 'N/A')
            }
        except:
            return {"name": ticker, "industry": "N/A"}