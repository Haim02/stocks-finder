import pandas_ta as ta
import yfinance as yf # הוספנו כדי להוציא נתוני דוחות
from typing import Optional, Dict
from app.models.schemas import TechnicalChecklist, TradePlan
from app.core.config import settings

class TAEngine:
    def __init__(self, ticker: str, data: dict):
        self.ticker = ticker # הוספנו טיקר כדי למשוך פונדמנטלי
        self.df_w = data.get("weekly")
        self.df_d = data.get("daily")
        self.df_h4 = data.get("h4")

    def get_fundamentals(self) -> dict:
        """מושך את הנתונים שמופיעים בטבלה במייל שלך"""
        try:
            stock = yf.Ticker(self.ticker)
            info = stock.info
            return {
                "pe_ratio": info.get("trailingPE", "N/A"),
                "revenue_growth": info.get("revenueGrowth", "N/A"),
                "earnings_growth": info.get("earningsGrowth", "N/A"),
                "fcf": info.get("freeCashflow", "N/A")
            }
        except:
            return {"pe_ratio": "N/A", "revenue_growth": "N/A", "earnings_growth": "N/A", "fcf": "N/A"}

    # def analyze(self) -> Optional[dict]:
    #     if self.df_w is None or self.df_d is None or self.df_h4 is None:
    #         return None

    #     # --- חישוב אינדיקטורים ל-Daily ---
    #     self.df_d['SMA200'] = ta.sma(self.df_d['Close'], length=200)
    #     self.df_d['SMA50'] = ta.sma(self.df_d['Close'], length=50)
    #     self.df_d['EMA20'] = ta.ema(self.df_d['Close'], length=20)
    #     self.df_d['RSI'] = ta.rsi(self.df_d['Close'], length=14)
    #     self.df_d['Vol_MA20'] = ta.sma(self.df_d['Volume'], length=20)

    #     last_close = self.df_d['Close'].iloc[-1]

    #     # --- צ'ק ליסט לפי האסטרטגיה שלך ---
    #     checklist = TechnicalChecklist(
    #         weekly_trend_up = self.df_w['Close'].iloc[-1] > ta.sma(self.df_w['Close'], length=50).iloc[-1] if len(self.df_w) > 50 else False,
    #         above_sma_200 = last_close > self.df_d['SMA200'].iloc[-1],
    #         above_sma_50 = last_close > self.df_d['SMA50'].iloc[-1],
    #         price_below_ema_20 = last_close < self.df_d['EMA20'].iloc[-1], # הפולבק מהסרטון
    #         rsi_value = self.df_d['RSI'].iloc[-1],
    #         rsi_ok = 40 <= self.df_d['RSI'].iloc[-1] <= 70,
    #         rel_volume_ok = self.df_d['Volume'].iloc[-1] > (self.df_d['Vol_MA20'].iloc[-1] * 1.2)
    #     )

    #     # חישוב ציון (Score)
    #     score = sum([
    #         checklist.weekly_trend_up, checklist.above_sma_200,
    #         checklist.above_sma_50, checklist.price_below_ema_20,
    #         checklist.rsi_ok, checklist.rel_volume_ok
    #     ])

    #     # אם הציון גבוה מ-4, בונים תוכנית מסחר ומוסיפים פונדמנטלי
    #     if score >= 4:
    #         plan = self.generate_trade_plan(last_close)
    #         fundamentals = self.get_fundamentals()
    #         return {
    #             "checklist": checklist,
    #             "plan": plan,
    #             "score": score,
    #             "fundamentals": fundamentals
    #         }

    #     return None



# import pandas as pd
# import pandas_ta as ta

# class TAEngine:
#     def __init__(self, ticker, data):
#         self.ticker = ticker
#         self.data = data

#     def analyze(self):
#         try:
#             # בדיקה: האם הנתונים הם בכלל DataFrame של פנדס?
#             if not isinstance(self.data, pd.DataFrame):
#                 print(f"⚠️ {self.ticker}: Data is not a DataFrame (received {type(self.data)})")
#                 return {'score': 0, 'reason': 'Invalid data format'}

#             # בדיקה: האם ה-DataFrame ריק או קטן מדי?
#             if self.data.empty or len(self.data) < 20:
#                 return {'score': 0, 'reason': 'Data is empty or too short'}

#             # חילוץ מחיר סגירה אחרון
#             close_price = float(self.data['Close'].iloc[-1])

#             # חישוב אינדיקטורים בזהירות
#             # SMA 200
#             sma200_series = ta.sma(self.data['Close'], length=200)
#             sma200 = sma200_series.iloc[-1] if (sma200_series is not None and len(sma200_series) > 0) else None

#             # EMA 21
#             ema21_series = ta.ema(self.data['Close'], length=21)
#             ema21 = ema21_series.iloc[-1] if (ema21_series is not None and len(ema21_series) > 0) else None

#             # RSI
#             rsi_series = ta.rsi(self.data['Close'], length=14)
#             rsi = rsi_series.iloc[-1] if (rsi_series is not None and len(rsi_series) > 0) else 50

#             score = 0
#             reasons = []

#             # לוגיקה למתן ציון (מעל 1 נשלח מייל)
#             if sma200 is not None and close_price > sma200:
#                 score += 2
#                 reasons.append("Trend: Above SMA200")

#             if ema21 is not None:
#                 diff = abs(close_price - ema21) / ema21
#                 if diff < 0.05: # בטווח של 5% מהממוצע
#                     score += 2
#                     reasons.append("Setup: Near EMA21 (Pullback)")

#             if rsi < 70:
#                 score += 1
#                 reasons.append(f"RSI: {round(rsi, 2)} (Not Overbought)")

#             return {
#                 'ticker': self.ticker,
#                 'score': score,
#                 'price': round(close_price, 2),
#                 'reasons': reasons
#             }

#         except Exception as e:
#             print(f"⚠️ Error in TA logic for {self.ticker}: {e}")
#             return {'score': 0, 'reason': str(e)}




# import pandas as pd
# import pandas_ta as ta

# class TAEngine:
#     def __init__(self, ticker, df):
#         self.ticker = ticker
#         self.df = df

#     def analyze(self):
#         df = self.df
#         if df is None or len(df) < 50:
#             return None

#         df.columns = [col.lower() for col in df.columns]

#         # --- חישוב אינדיקטורים (זהה ל-Pinescript) ---
#         df['ma20'] = ta.sma(df['close'], length=20)
#         df['ma50'] = ta.sma(df['close'], length=50)
#         df['rsi'] = ta.rsi(df['close'], length=14)

#         # ווליום וממוצע ווליום (10 ימים)
#         df['avg_vol_10'] = ta.sma(df['volume'], length=10)

#         # נתונים לנר הנוכחי ולנר הקודם
#         last = df.iloc[-1]
#         prev = df.iloc[-2]

#         # ווליום יחסי
#         rel_vol = last['volume'] / last['avg_vol_10'] if last['avg_vol_10'] > 0 else 0

#         # --- לוגיקת האסטרטגיה (Swing Webhook logic) ---
#         reasons = []
#         score = 0

#         # 1. Trend UP (Price > MA50 and MA20 > MA50)
#         is_trend_up = last['close'] > last['ma50'] and last['ma20'] > last['ma50']
#         if is_trend_up:
#             score += 1
#             reasons.append("Trend UP (Price > MA50 & MA20 > MA50)")

#         # 2. Volume Filter (Avg > 500k and Rel Vol > 1.2)
#         vol_ok = last['avg_vol_10'] >= 500000 and rel_vol >= 1.2
#         if vol_ok:
#             score += 1
#             reasons.append(f"High Volume (Rel Vol: {rel_vol:.2f}x)")

#         # 3. BREAKOUT (Crossover MA50)
#         if prev['close'] <= prev['ma50'] and last['close'] > last['ma50']:
#             score += 2
#             reasons.append("MA50 Breakout")

#         # 4. REBOUND (RSI crossover 30)
#         if prev['rsi'] <= 30 and last['rsi'] > 30:
#             score += 2
#             reasons.append("RSI Rebound from Oversold")

#         # 5. Momentum (RSI > 50)
#         if last['rsi'] > 50:
#             score += 1
#             reasons.append("Bullish Momentum (RSI > 50)")

#         # חישוב תמיכה בסיסי (Pivot Low - מינימום של 5 נרות אחרונים)
#         support = df['low'].tail(5).min()

#         return {
#             "ticker": self.ticker,
#             "price": float(last['close']),
#             "score": score,
#             "reasons": reasons,
#             "sma_20": float(last['ma20']),
#             "sma_50": float(last['ma50']),
#             "rsi": float(last['rsi']),
#             "rel_vol": float(rel_vol),
#             "support": float(support)
#         }



# import pandas as pd
# import pandas_ta as ta

# class TAEngine:
#     def __init__(self, ticker, df):
#         self.ticker = ticker
#         self.df = df

#     def analyze(self):
#         df = self.df
#         if df is None or len(df) < 50:
#             return None

#         df.columns = [col.lower() for col in df.columns]

#         # --- אינדיקטורים בסיסיים ---
#         df['ma20'] = ta.sma(df['close'], length=20)
#         df['ma50'] = ta.sma(df['close'], length=50)
#         df['rsi'] = ta.rsi(df['close'], length=14)
#         df['avg_vol_10'] = ta.sma(df['volume'], length=10)

#         # --- הוספת רצועות בולינג'ר לזיהוי דחיסה (Squeeze) ---
#         bbands = ta.bbands(df['close'], length=20, std=2)
#         df['bb_lower'] = bbands['BBL_20_2.0']
#         df['bb_upper'] = bbands['BBU_20_2.0']
#         df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['ma20'] # רוחב הרצועות

#         last = df.iloc[-1]
#         prev = df.iloc[-2]

#         reasons = []
#         score = 0

#         # 1. זיהוי דחיסה (Squeeze) - רצועות בולינג'ר צרות מאוד (מתחת לממוצע ההיסטורי)
#         avg_width = df['bb_width'].tail(20).mean()
#         is_squeezing = last['bb_width'] < avg_width * 0.8 # דחיסה של 20% מהממוצע

#         # 2. פריצה טרייה של ממוצע 20 (Early Signal)
#         is_fresh_breakout = prev['close'] <= last['ma20'] and last['close'] > last['ma20']

#         # 3. ווליום מתגבר (יותר מ-1.1 מהממוצע)
#         rel_vol = last['volume'] / last['avg_vol_10'] if last['avg_vol_10'] > 0 else 0

#         # --- לוגיקת הציון החדשה (Early Bird) ---

#         # אם יש דחיסה והתחלה של פריצה - זה ה-Sweet Spot
#         if is_squeezing and last['close'] > last['ma20']:
#             score += 2
#             reasons.append("Volatility Squeeze (Potential Explosion)")

#         if is_fresh_breakout:
#             score += 2
#             reasons.append("Fresh MA20 Breakout (Early Entry)")

#         if rel_vol > 1.2:
#             score += 1
#             reasons.append(f"Volume Pickup ({rel_vol:.1f}x)")

#         # תמיכה טכנית (השפל של 5 הימים האחרונים)
#         support = df['low'].tail(5).min()

#         # אם המניה כבר עלתה יותר מדי (RSI > 70), נוריד ציון כדי לא להיכנס בשיא
#         if last['rsi'] > 70:
#             score -= 1
#             reasons.append("Overbought (Caution: Extension)")

#         return {
#             "ticker": self.ticker,
#             "price": float(last['close']),
#             "score": score,
#             "reasons": reasons,
#             "sma_20": float(last['ma20']),
#             "sma_50": float(last['ma50']),
#             "rsi": float(last['rsi']),
#             "rel_vol": float(rel_vol),
#             "support": float(support),
#             "is_early": is_fresh_breakout or is_squeezing
#         }



import pandas as pd
import pandas_ta as ta

class TAEngine:
    def __init__(self, ticker, df):
        self.ticker = ticker
        self.df = df

    def analyze(self):
        df = self.df
        # בדיקה שיש מספיק נתונים
        if df is None or len(df) < 50:
            return None

        # המרת שמות עמודות לאותיות קטנות (למניעת שגיאות)
        df.columns = [col.lower() for col in df.columns]

        try:
            # --- אינדיקטורים בסיסיים ---
            df['ma20'] = ta.sma(df['close'], length=20)
            df['ma50'] = ta.sma(df['close'], length=50)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['avg_vol'] = ta.sma(df['volume'], length=10)

            # --- תיקון השגיאה: חישוב בולינג'ר ---
            bbands = ta.bbands(df['close'], length=20, std=2)

            if bbands is None or bbands.empty:
                return None

            # במקום להסתמך על שמות (כמו 'BBU_20_2.0'), ניקח לפי מיקום:
            # עמודה 0 = רצועה תחתונה (Lower)
            # עמודה 1 = ממוצע (Middle)
            # עמודה 2 = רצועה עליונה (Upper)
            df['bb_lower'] = bbands.iloc[:, 0]
            df['bb_upper'] = bbands.iloc[:, 2]

            # חישוב רוחב הרצועות (Squeeze Check)
            # טיפול במקרה של חלוקה באפס
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['ma20']

        except Exception as e:
            print(f"⚠️ Calculation Error for {self.ticker}: {e}")
            return None

        # נתונים אחרונים
        last = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0
        reasons = []

        # וודא שהנתונים קיימים (לא NaN)
        if pd.isna(last['bb_width']) or pd.isna(last['rsi']):
            return None

        # 1. בדיקת Squeeze (האם הרצועות צרות מהממוצע?)
        avg_width = df['bb_width'].tail(20).mean()
        is_squeezing = last['bb_width'] < (avg_width * 0.9) # צר ב-10% מהרגיל

        # 2. בדיקת פריצה מוקדמת (Fresh Breakout)
        # המחיר חצה את ה-20 למעלה היום או אתמול
        crossed_ma20 = (prev['close'] < last['ma20'] and last['close'] > last['ma20']) or \
                       (last['low'] < last['ma20'] and last['close'] > last['ma20'])

        # 3. בדיקת ווליום
        rel_vol = last['volume'] / last['avg_vol'] if last['avg_vol'] > 0 else 0

        # --- מתן ניקוד לזיהוי מוקדם ---

        if is_squeezing:
            score += 2
            reasons.append("Volatility Squeeze (Energy Building)")

        if crossed_ma20:
            score += 2
            reasons.append("Fresh MA20 Breakout")

        if rel_vol > 1.2:
            score += 1
            reasons.append(f"High Volume ({rel_vol:.1f}x)")

        # הגנה: אם המניה כבר טסה (RSI > 70), אל תיתן לה ציון גבוה
        if last['rsi'] > 70:
            score -= 2
            reasons.append("Overbought (Too Late?)")
        elif last['rsi'] > 50 and last['rsi'] < 70:
            score += 1 # זה הטווח המושלם

        # מציאת תמיכה לסטופ-לוס (הנמוך של 5 ימים אחרונים)
        support = df['low'].tail(5).min()

        return {
            "ticker": self.ticker,
            "price": float(last['close']),
            "score": score,
            "reasons": reasons,
            "support": float(support),
            "rsi": float(last['rsi']),
            "squeeze": is_squeezing
        }