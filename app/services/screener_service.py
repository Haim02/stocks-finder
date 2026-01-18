from tradingview_screener import Query, Column
import pandas as pd

class ScreenerService:
    @staticmethod
    def get_candidates():
        print("🔍 Scanning TradingView for candidates (Real-time)...")

        try:
            # 1. הגדרת השאילתה
            q = Query().set_markets('america')

            # 2. בחירה מפורשת של העמודות
            q.select('name', 'close', 'volume', 'market_cap_basic')

            # 3. הסינונים (כאן ה-WHERE שהיה חסר לך!)
            q.where(
                Column('close') > 2.0,                     # סינון קריטי: רק מניות מעל 2 דולר
                Column('close') > Column('SMA200'),        # מניות במגמת עליה בלבד
                Column('relative_volume_10d_calc') > 1.2,  # ווליום חריג
                Column('type') == 'stock',                 # רק מניות (בלי תעודות סל)
                Column('average_volume_10d_calc') > 500000 # נזילות גבוהה
            )

            # מיון: אנחנו רוצים את אלו שזזו הכי חזק היום
            q.order_by('change', ascending=False)
            q.limit(30)

            # 4. קבלת נתונים
            response = q.get_scanner_data()

            if not response or len(response) < 2:
                print("⚠️ No results returned.")
                return []

            rows = response[1]
            tickers = []

            # --- זיהוי פורמט (DataFrame או List) ---
            if hasattr(rows, 'columns') and hasattr(rows, 'iloc'):
                # מקרה א': קיבלנו טבלה של פנדס
                if 'name' in rows.columns:
                    tickers = rows['name'].tolist()
                elif 'ticker' in rows.columns:
                    tickers = rows['ticker'].tolist()
            else:
                # מקרה ב': קיבלנו רשימה רגילה
                for row in rows:
                    ticker = None
                    if isinstance(row, dict):
                        ticker = row.get('name')
                    elif hasattr(row, 'name'):
                        ticker = row.name
                    elif isinstance(row, list) and len(row) > 0:
                        ticker = row[0]

                    if ticker:
                        tickers.append(ticker)

            # --- ניקוי סופי ---
            clean_tickers = []
            for t in tickers:
                if isinstance(t, str):
                    # מנקה זבל כמו "NASDAQ:AAPL" -> "AAPL"
                    clean_t = t.split(":")[-1].strip()
                    # מוודא שזה לא כותרת
                    if clean_t.lower() not in ['name', 'ticker', 'close', 'volume', 'n/a']:
                        clean_tickers.append(clean_t)

            # הסרת כפילויות
            final_tickers = list(set(clean_tickers))

            print(f"✅ Found {len(final_tickers)} valid stocks (> $2): {final_tickers}")
            return final_tickers

        except Exception as e:
            print(f"❌ Error in Screener Logic: {e}")
            return []