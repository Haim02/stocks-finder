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




from tradingview_screener import Query, Column
import pandas as pd

class ScreenerService:
    @staticmethod
    def get_candidates():
        print("🔍 Scanning TradingView for Early Breakout candidates (High Relative Vol)...")

        try:
            q = Query().set_markets('america')

            q.select('name', 'close', 'volume', 'market_cap_basic')

            q.where(
                Column('close') > 5.0,                         # סינון מניות זבל (מעל 5$)
                Column('close') > Column('SMA200'),            # מגמת עליה ראשית (חובה)
                Column('average_volume_10d_calc') > 750000,    # נזילות גבוהה מאוד
                Column('relative_volume_10d_calc') > 1.2,      # ווליום גבוה ב-20% מהרגיל (סימן לכניסת כסף)
                Column('type') == 'stock'
            )

            # שינוי קריטי: מיון לפי ווליום יחסי במקום לפי אחוז שינוי!
            # זה מביא מניות שמתבשל בהן מהלך, גם אם הן עוד לא טסו 10%
            q.order_by('relative_volume_10d_calc', ascending=False)
            q.limit(35)

            response = q.get_scanner_data()

            if not response or len(response) < 2:
                print("⚠️ No results returned.")
                return []

            rows = response[1]
            tickers = []

            if hasattr(rows, 'columns') and hasattr(rows, 'iloc'):
                if 'name' in rows.columns:
                    tickers = rows['name'].tolist()
                elif 'ticker' in rows.columns:
                    tickers = rows['ticker'].tolist()
            else:
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

            # ניקוי
            clean_tickers = []
            for t in tickers:
                if isinstance(t, str):
                    clean_t = t.split(":")[-1].strip()
                    if clean_t.lower() not in ['name', 'ticker', 'close', 'volume', 'n/a']:
                        clean_tickers.append(clean_t)

            final_tickers = list(set(clean_tickers))
            print(f"✅ Found {len(final_tickers)} potential early-movers: {final_tickers}")
            return final_tickers

        except Exception as e:
            print(f"❌ Error in Screener Logic: {e}")
            return []