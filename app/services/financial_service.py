# import finnhub
# import yfinance as yf
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         if not settings.FINNHUB_API_KEY:
#             raise ValueError("Missing FINNHUB_API_KEY in .env")
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)

#     def analyze(self, ticker):
#         """
#         גרסה מותאמת למנויים חינמיים ב-Finnhub.
#         משתמשת ב-Finnhub למחיר ומדדים, וב-yfinance לדוחות עומק.
#         """
#         try:
#             # 1. נתונים מ-Finnhub (מותרים בחינם)
#             basic = self.client.company_basic_financials(ticker, 'all')
#             metric = basic.get('metric', {})

#             # אם אין נתונים בסיסיים, נדלג
#             if not metric:
#                 return None

#             # נתונים מ-Finnhub (Metric Endpoint הוא חינמי)
#             rev_growth = metric.get('revenueGrowthQuarterlyYoy', 0)
#             beta = metric.get('beta', 1.2) # ברירת מחדל אם אין

#             # 2. השלמת נתונים מ-yfinance (כי Finnhub חוסם דוחות היסטוריים בחינם)
#             # אנחנו צריכים את זה לחישוב התייעלות (Efficiency)
#             stock_yf = yf.Ticker(ticker)
#             try:
#                 hist_price = stock_yf.history(period="1d")
#                 current_price = hist_price['Close'].iloc[-1]
#             except:
#                 # גיבוי אם yfinance נכשל, ננסה לקחת מ-Finnhub (ציטוט בזמן אמת)
#                 quote = self.client.quote(ticker)
#                 current_price = quote.get('c', 0)

#             # חישוב יעדים טכניים
#             volatility_buffer = beta * 0.04
#             target_price = current_price * (1 + (volatility_buffer * 2.5))
#             stop_loss = current_price * (1 - volatility_buffer)

#             return {
#                 "current_price": round(current_price, 2),
#                 "market_cap": metric.get('marketCapitalization', 0),
#                 "revenue_growth": round(rev_growth, 2) if rev_growth else 0,
#                 # סנטימנט: בגלל שזה חסום בחינם, נחזיר ערך ניטרלי או נמחק
#                 "sentiment_bullish_pct": 50,
#                 "target_price": round(target_price, 2),
#                 "stop_loss": round(stop_loss, 2),
#                 "source": "Hybrid (Finnhub Free + YFinance)"
#             }

#         except Exception as e:
#             print(f"⚠️ Data Error for {ticker}: {e}")
#             return None


# import finnhub
# import yfinance as yf
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         if not settings.FINNHUB_API_KEY:
#             print("⚠️ Warning: FINNHUB_API_KEY missing.")
#         # נשתמש ב-Finnhub רק אם יש מפתח, אחרת נסתמך על yfinance
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

#     def analyze(self, ticker):
#         try:
#             # 1. משיכת נתונים מ-yfinance (הכלי המרכזי לדוחות)
#             stock_yf = yf.Ticker(ticker)
#             info = stock_yf.info

#             # בדיקה שהמניה קיימת
#             current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
#             if not current_price:
#                 return None

#             # 2. חילוץ תיאור חברה
#             description = info.get('longBusinessSummary', 'No description available.')
#             # קיצור התיאור אם הוא ארוך מדי
#             if len(description) > 250:
#                 description = description[:250] + "..."

#             # 3. חישוב התייעלות וצמיחה (רבעון מול רבעון)
#             q_fin = stock_yf.quarterly_financials

#             growth_qoq = 0
#             efficiency_data = None

#             # וודא שיש מספיק נתונים (לפחות 2 עמודות/רבעונים)
#             if not q_fin.empty and q_fin.shape[1] >= 2:
#                 try:
#                     # רבעון אחרון (0) ורבעון לפניו (1)
#                     # שימוש ב-iloc כדי לקחת לפי מיקום ולא לפי שם
#                     rev_curr = q_fin.loc['Total Revenue'].iloc[0]
#                     rev_prev = q_fin.loc['Total Revenue'].iloc[1]

#                     # הוצאות תפעוליות (לפעמים נקראות בשמות שונים, ננסה למצוא)
#                     if 'Total Operating Expenses' in q_fin.index:
#                         exp_curr = q_fin.loc['Total Operating Expenses'].iloc[0]
#                         exp_prev = q_fin.loc['Total Operating Expenses'].iloc[1]
#                     else:
#                         # חישוב עקיף אם אין שורה מפורשת: הכנסות פחות רווח תפעולי
#                         op_inc_curr = q_fin.loc['Operating Income'].iloc[0]
#                         op_inc_prev = q_fin.loc['Operating Income'].iloc[1]
#                         exp_curr = rev_curr - op_inc_curr
#                         exp_prev = rev_prev - op_inc_prev

#                     # חישוב צמיחה בהכנסות
#                     growth_qoq = ((rev_curr - rev_prev) / rev_prev) * 100

#                     # חישוב יחס התייעלות (Efficiency Ratio = Exp / Rev)
#                     # ככל שנמוך יותר = טוב יותר
#                     eff_curr_ratio = (exp_curr / rev_curr) * 100
#                     eff_prev_ratio = (exp_prev / rev_prev) * 100

#                     efficiency_data = {
#                         "curr_ratio": round(eff_curr_ratio, 1),
#                         "prev_ratio": round(eff_prev_ratio, 1),
#                         "change": round(eff_curr_ratio - eff_prev_ratio, 1), # שלילי = שיפור
#                         "is_improving": eff_curr_ratio < eff_prev_ratio
#                     }
#                 except Exception as e:
#                     print(f"⚠️ Error calculating metrics for {ticker}: {e}")

#             # 4. יעדי מחיר וסטופ (לפי תנודתיות בטא)
#             beta = info.get('beta', 1.5)
#             # אם אין בטא, נניח תנודתיות בינונית
#             if not beta: beta = 1.5

#             volatility_buffer = beta * 0.04
#             target_price = current_price * (1 + (volatility_buffer * 2.0))
#             stop_loss = current_price * (1 - volatility_buffer)

#             return {
#                 "current_price": round(current_price, 2),
#                 "market_cap": info.get('marketCap', 0),
#                 "description": description,
#                 "sector": info.get('sector', 'N/A'),
#                 "industry": info.get('industry', 'N/A'),
#                 "revenue_growth_qoq": round(growth_qoq, 2),
#                 "efficiency": efficiency_data,
#                 "target_price": round(target_price, 2),
#                 "stop_loss": round(stop_loss, 2)
#             }

#         except Exception as e:
#             print(f"⚠️ Financial Data Error for {ticker}: {e}")
#             return None


# import finnhub
# import yfinance as yf
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

#     def analyze(self, ticker):
#         try:
#             stock_yf = yf.Ticker(ticker)
#             info = stock_yf.info
#             current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
#             if not current_price: return None

#             # תיאור באנגלית (נשלח ל-AI לתרגום אח"כ)
#             description = info.get('longBusinessSummary', '')[:400]

#             # דוחות כספיים
#             q_fin = stock_yf.quarterly_financials

#             growth_qoq = 0
#             efficiency_data = None
#             raw_revenue = {"curr": 0, "prev": 0} # נתונים גולמיים לתצוגה

#             if not q_fin.empty and q_fin.shape[1] >= 2:
#                 try:
#                     # 1. חיפוש חכם של שורת ההכנסות
#                     rev_row = None
#                     possible_keys = ['Total Revenue', 'Operating Revenue', 'Revenue', 'Total Income']

#                     for key in possible_keys:
#                         if key in q_fin.index:
#                             rev_row = q_fin.loc[key]
#                             break

#                     if rev_row is not None:
#                         rev_curr = rev_row.iloc[0]
#                         rev_prev = rev_row.iloc[1]

#                         # שמירת הנתונים הגולמיים למייל
#                         raw_revenue["curr"] = rev_curr
#                         raw_revenue["prev"] = rev_prev

#                         # חישוב צמיחה
#                         if rev_prev > 0:
#                             growth_qoq = ((rev_curr - rev_prev) / rev_prev) * 100

#                         # 2. חישוב התייעלות (הוצאות)
#                         exp_curr = 0
#                         exp_prev = 0

#                         # ניסיון למצוא הוצאות תפעוליות
#                         if 'Total Operating Expenses' in q_fin.index:
#                             exp_curr = q_fin.loc['Total Operating Expenses'].iloc[0]
#                             exp_prev = q_fin.loc['Total Operating Expenses'].iloc[1]
#                         elif 'Operating Income' in q_fin.index:
#                             # אם אין הוצאות מפורשות: הכנסות פחות רווח תפעולי
#                             exp_curr = rev_curr - q_fin.loc['Operating Income'].iloc[0]
#                             exp_prev = rev_prev - q_fin.loc['Operating Income'].iloc[1]

#                         if rev_curr > 0 and rev_prev > 0:
#                             eff_curr_ratio = (exp_curr / rev_curr) * 100
#                             eff_prev_ratio = (exp_prev / rev_prev) * 100

#                             efficiency_data = {
#                                 "curr_ratio": round(eff_curr_ratio, 1),
#                                 "prev_ratio": round(eff_prev_ratio, 1),
#                                 "is_improving": eff_curr_ratio < eff_prev_ratio
#                             }

#                 except Exception as e:
#                     print(f"⚠️ Calculation Error {ticker}: {e}")

#             # יעדים
#             beta = info.get('beta', 1.5) or 1.5
#             volatility = beta * 0.04
#             target_price = current_price * (1 + (volatility * 2.0))
#             stop_loss = current_price * (1 - volatility)

#             return {
#                 "current_price": round(current_price, 2),
#                 "market_cap": info.get('marketCap', 0),
#                 "description": description,
#                 "sector": info.get('sector', 'N/A'),
#                 "industry": info.get('industry', 'N/A'),
#                 "revenue_growth_qoq": round(growth_qoq, 2),
#                 "raw_revenue": raw_revenue, # הוספנו את זה לטבלה
#                 "efficiency": efficiency_data,
#                 "target_price": round(target_price, 2),
#                 "stop_loss": round(stop_loss, 2)
#             }

#         except Exception as e:
#             print(f"⚠️ Data Error {ticker}: {e}")
#             return None

# import finnhub
# import yfinance as yf
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

#     def analyze(self, ticker):
#         try:
#             stock_yf = yf.Ticker(ticker)
#             info = stock_yf.info
#             current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
#             if not current_price: return None

#             description = info.get('longBusinessSummary', '')[:400]
#             q_fin = stock_yf.quarterly_financials

#             financial_data = {
#                 "current_price": round(current_price, 2),
#                 "market_cap": info.get('marketCap', 0),
#                 "description": description,
#                 "sector": info.get('sector', 'N/A'),
#                 "industry": info.get('industry', 'N/A'),
#                 "target_price": 0,
#                 "stop_loss": 0,
#                 "revenue": {"curr": 0, "prev": 0, "change": 0},
#                 "net_income": {"curr": 0, "prev": 0, "change": 0},
#                 # התיקון: החלפנו ריבית בהתייעלות תפעולית
#                 "efficiency": {"curr": None, "prev": None}
#             }

#             if not q_fin.empty and q_fin.shape[1] >= 2:
#                 try:
#                     def get_value(key, col_idx):
#                         if key in q_fin.index:
#                             return q_fin.loc[key].iloc[col_idx]
#                         return 0

#                     # 1. הכנסות
#                     rev_curr = get_value('Total Revenue', 0) or get_value('Operating Revenue', 0)
#                     rev_prev = get_value('Total Revenue', 1) or get_value('Operating Revenue', 1)

#                     if rev_prev != 0:
#                         rev_change = ((rev_curr - rev_prev) / rev_prev) * 100
#                     else:
#                         rev_change = 0

#                     financial_data["revenue"] = {"curr": rev_curr, "prev": rev_prev, "change": round(rev_change, 2)}

#                     # 2. רווח נקי
#                     ni_curr = get_value('Net Income', 0)
#                     ni_prev = get_value('Net Income', 1)

#                     if ni_prev != 0:
#                         ni_change = ((ni_curr - ni_prev) / abs(ni_prev)) * 100
#                     else:
#                         ni_change = 0

#                     financial_data["net_income"] = {"curr": ni_curr, "prev": ni_prev, "change": round(ni_change, 2)}

#                     # 3. חישוב התייעלות תפעולית (הוצאות / הכנסות)
#                     # ננסה למצוא את סך ההוצאות התפעוליות
#                     op_exp_curr = get_value('Total Operating Expenses', 0)
#                     op_exp_prev = get_value('Total Operating Expenses', 1)

#                     # גיבוי: אם אין שורה מפורשת, נחשב: הכנסות פחות רווח תפעולי
#                     if op_exp_curr == 0:
#                         op_inc_curr = get_value('Operating Income', 0)
#                         op_exp_curr = rev_curr - op_inc_curr

#                     if op_exp_prev == 0:
#                         op_inc_prev = get_value('Operating Income', 1)
#                         op_exp_prev = rev_prev - op_inc_prev

#                     # חישוב היחס באחוזים
#                     def calc_eff(exp, rev):
#                         if rev and rev != 0:
#                             return round((exp / rev) * 100, 2)
#                         return None

#                     financial_data["efficiency"]["curr"] = calc_eff(op_exp_curr, rev_curr)
#                     financial_data["efficiency"]["prev"] = calc_eff(op_exp_prev, rev_prev)

#                 except Exception as e:
#                     print(f"⚠️ Calculation Error {ticker}: {e}")

#             # יעדי מחיר
#             beta = info.get('beta', 1.5) or 1.5
#             volatility = beta * 0.04
#             financial_data["target_price"] = round(current_price * (1 + (volatility * 2.0)), 2)
#             financial_data["stop_loss"] = round(current_price * (1 - volatility), 2)

#             return financial_data

#         except Exception as e:
#             print(f"⚠️ Data Error {ticker}: {e}")
#             return None



# import finnhub
# import yfinance as yf
# import pandas as pd
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

#     def analyze(self, ticker):
#         try:
#             stock_yf = yf.Ticker(ticker)
#             info = stock_yf.info
#             current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
#             if not current_price: return None

#             description = info.get('longBusinessSummary', '')[:400]
#             q_fin = stock_yf.quarterly_financials

#             # --- 1. בדיקה טכנית משולבת (SMA 150 + Breakout) ---
#             technical_signal = "ללא איתות מיוחד"
#             trend_status = "מגמה שלילית/דשדוש" # ברירת מחדל

#             try:
#                 # משיכת שנה אחורה (חובה בשביל SMA 150)
#                 hist = stock_yf.history(period="1y")

#                 if len(hist) > 150:
#                     # חישוב ממוצעים
#                     hist['SMA50'] = hist['Close'].rolling(window=50).mean()
#                     hist['SMA150'] = hist['Close'].rolling(window=150).mean()

#                     curr_close = hist['Close'].iloc[-1]
#                     prev_close = hist['Close'].iloc[-2]

#                     curr_sma50 = hist['SMA50'].iloc[-1]
#                     curr_sma150 = hist['SMA150'].iloc[-1]

#                     # בדיקת ווליום
#                     avg_vol = hist['Volume'].mean()
#                     curr_vol = hist['Volume'].iloc[-1]
#                     vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0

#                     # --- בדיקה 1: האם המגמה הראשית חיובית? (מעל SMA 150) ---
#                     is_uptrend = curr_close > curr_sma150

#                     if is_uptrend:
#                         trend_status = "✅ מגמה ראשית עולה (מעל SMA150)"

#                         # --- בדיקה 2: האם יש איתות כניסה? (פריצת SMA 50) ---
#                         # תנאי: אתמול מתחת ל-50, היום מעל ל-50 + ווליום
#                         if prev_close < curr_sma50 and curr_close > curr_sma50:
#                             if vol_ratio > 1.2:
#                                 technical_signal = f"🔥 פריצת SMA50 בווליום גבוה (x{vol_ratio:.1f})"
#                             else:
#                                 technical_signal = "⚠️ פריצת SMA50 ללא ווליום"

#                         # איתות מומנטום חזק (כבר מעל הממוצעים וטס למעלה)
#                         elif curr_close > curr_sma50 and vol_ratio > 2.0:
#                              technical_signal = f"🚀 מומנטום חזק בווליום גבוה (x{vol_ratio:.1f})"
#                     else:
#                         trend_status = "⛔ מתחת ל-SMA150 (מסוכן ללונג)"

#             except Exception as e:
#                 print(f"Technical analysis failed: {e}")

#             # --- סוף ניתוח טכני ---

#             financial_data = {
#                 "current_price": round(current_price, 2),
#                 "market_cap": info.get('marketCap', 0),
#                 "description": description,
#                 "sector": info.get('sector', 'N/A'),
#                 "industry": info.get('industry', 'N/A'),
#                 "target_price": 0,
#                 "stop_loss": 0,
#                 "revenue": {"curr": 0, "prev": 0, "change": 0},
#                 "net_income": {"curr": 0, "prev": 0, "change": 0},
#                 "efficiency": {"curr": None, "prev": None},
#                 # הנתונים החדשים למייל
#                 "technical_signal": technical_signal,
#                 "trend_status": trend_status
#             }

#             if not q_fin.empty and q_fin.shape[1] >= 2:
#                 try:
#                     def get_value(key, col_idx):
#                         if key in q_fin.index:
#                             return q_fin.loc[key].iloc[col_idx]
#                         return 0

#                     # הכנסות
#                     rev_curr = get_value('Total Revenue', 0) or get_value('Operating Revenue', 0)
#                     rev_prev = get_value('Total Revenue', 1) or get_value('Operating Revenue', 1)
#                     if rev_prev != 0:
#                         rev_change = ((rev_curr - rev_prev) / rev_prev) * 100
#                     else:
#                         rev_change = 0
#                     financial_data["revenue"] = {"curr": rev_curr, "prev": rev_prev, "change": round(rev_change, 2)}

#                     # רווח נקי
#                     ni_curr = get_value('Net Income', 0)
#                     ni_prev = get_value('Net Income', 1)
#                     if ni_prev != 0:
#                         ni_change = ((ni_curr - ni_prev) / abs(ni_prev)) * 100
#                     else:
#                         ni_change = 0
#                     financial_data["net_income"] = {"curr": ni_curr, "prev": ni_prev, "change": round(ni_change, 2)}

#                     # התייעלות
#                     op_exp_curr = get_value('Total Operating Expenses', 0)
#                     op_exp_prev = get_value('Total Operating Expenses', 1)

#                     if op_exp_curr == 0:
#                         op_exp_curr = rev_curr - get_value('Operating Income', 0)
#                     if op_exp_prev == 0:
#                         op_exp_prev = rev_prev - get_value('Operating Income', 1)

#                     def calc_eff(exp, rev):
#                         if rev and rev != 0:
#                             return round((exp / rev) * 100, 2)
#                         return None

#                     financial_data["efficiency"]["curr"] = calc_eff(op_exp_curr, rev_curr)
#                     financial_data["efficiency"]["prev"] = calc_eff(op_exp_prev, rev_prev)

#                 except Exception as e:
#                     print(f"⚠️ Calculation Error {ticker}: {e}")

#             # יעדים
#             beta = info.get('beta', 1.5) or 1.5
#             volatility = beta * 0.04
#             financial_data["target_price"] = round(current_price * (1 + (volatility * 2.0)), 2)
#             financial_data["stop_loss"] = round(current_price * (1 - volatility), 2)

#             return financial_data

#         except Exception as e:
#             print(f"⚠️ Data Error {ticker}: {e}")
#             return None



# import finnhub
# import yfinance as yf
# import pandas as pd
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

#     def analyze(self, ticker):
#         try:
#             stock_yf = yf.Ticker(ticker)
#             info = stock_yf.info
#             current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
#             if not current_price: return None

#             description = info.get('longBusinessSummary', '')[:400]
#             q_fin = stock_yf.quarterly_financials

#             # --- משתנים טכניים ---
#             technical_signal = "ללא איתות מיוחד"
#             trend_status = "מגמה לא ברורה"

#             try:
#                 # 1. משיכת היסטוריה (שנה אחורה חובה ל-150)
#                 hist = stock_yf.history(period="1y")

#                 if len(hist) > 150:
#                     # חישוב ממוצעים
#                     hist['SMA50'] = hist['Close'].rolling(window=50).mean()
#                     hist['SMA150'] = hist['Close'].rolling(window=150).mean()

#                     # נתונים נוכחיים (היום) וקודמים (אתמול)
#                     curr_close = hist['Close'].iloc[-1]
#                     prev_close = hist['Close'].iloc[-2]

#                     curr_sma50 = hist['SMA50'].iloc[-1]
#                     curr_sma150 = hist['SMA150'].iloc[-1] # הממוצע הקריטי

#                     # ווליום
#                     avg_vol = hist['Volume'].mean()
#                     curr_vol = hist['Volume'].iloc[-1]
#                     vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0

#                     # --- הבדיקה החדשה: חציית SMA 150 "טרייה" ---
#                     # תנאי 1: אתמול היינו מתחת ל-150
#                     was_below = prev_close < curr_sma150
#                     # תנאי 2: היום אנחנו מעל
#                     is_above = curr_close > curr_sma150
#                     # תנאי 3: לא ברחנו מדי (עד 3% מעל הממוצע)
#                     distance_pct = (curr_close - curr_sma150) / curr_sma150
#                     is_close = distance_pct < 0.03

#                     # בדיקת המגמה הכללית
#                     if curr_close > curr_sma150:
#                         trend_status = "✅ מעל SMA150 (חיובי)"
#                     else:
#                         trend_status = "⛔ מתחת ל-SMA150"

#                     # --- קביעת האיתות ---

#                     # 1. איתות הזהב: חצייה טרייה של 150
#                     if was_below and is_above and is_close:
#                         technical_signal = f"💎 חציית SMA150 טרייה! (+{distance_pct*100:.1f}%)"

#                     # 2. איתות כסף: פריצת SMA 50 בווליום
#                     elif prev_close < curr_sma50 and curr_close > curr_sma50 and vol_ratio > 1.2:
#                         technical_signal = f"🔥 פריצת SMA50 בווליום (x{vol_ratio:.1f})"

#                     # 3. סתם מומנטום
#                     elif curr_close > curr_sma50 and vol_ratio > 2.0:
#                         technical_signal = f"🚀 מומנטום חזק"

#             except Exception as e:
#                 print(f"Technical analysis failed: {e}")

#             # --- סוף ניתוח טכני ---

#             financial_data = {
#                 "current_price": round(current_price, 2),
#                 "market_cap": info.get('marketCap', 0),
#                 "description": description,
#                 "sector": info.get('sector', 'N/A'),
#                 "industry": info.get('industry', 'N/A'),
#                 "target_price": 0,
#                 "stop_loss": 0,
#                 "revenue": {"curr": 0, "prev": 0, "change": 0},
#                 "net_income": {"curr": 0, "prev": 0, "change": 0},
#                 "efficiency": {"curr": None, "prev": None},
#                 "technical_signal": technical_signal,
#                 "trend_status": trend_status
#             }

#             # --- חישובים פיננסיים (ללא שינוי) ---
#             if not q_fin.empty and q_fin.shape[1] >= 2:
#                 try:
#                     def get_value(key, col_idx):
#                         if key in q_fin.index: return q_fin.loc[key].iloc[col_idx]
#                         return 0

#                     # הכנסות
#                     rev_curr = get_value('Total Revenue', 0) or get_value('Operating Revenue', 0)
#                     rev_prev = get_value('Total Revenue', 1) or get_value('Operating Revenue', 1)
#                     financial_data["revenue"]["curr"] = rev_curr
#                     financial_data["revenue"]["prev"] = rev_prev
#                     if rev_prev != 0:
#                         financial_data["revenue"]["change"] = round(((rev_curr - rev_prev) / rev_prev) * 100, 2)

#                     # רווח נקי
#                     ni_curr = get_value('Net Income', 0)
#                     ni_prev = get_value('Net Income', 1)
#                     financial_data["net_income"]["curr"] = ni_curr
#                     financial_data["net_income"]["prev"] = ni_prev
#                     if ni_prev != 0:
#                         financial_data["net_income"]["change"] = round(((ni_curr - ni_prev) / abs(ni_prev)) * 100, 2)

#                     # התייעלות
#                     op_exp_curr = get_value('Total Operating Expenses', 0)
#                     op_exp_prev = get_value('Total Operating Expenses', 1)
#                     if op_exp_curr == 0: op_exp_curr = rev_curr - get_value('Operating Income', 0)
#                     if op_exp_prev == 0: op_exp_prev = rev_prev - get_value('Operating Income', 1)

#                     def calc_eff(exp, rev):
#                         if rev and rev != 0: return round((exp / rev) * 100, 2)
#                         return None

#                     financial_data["efficiency"]["curr"] = calc_eff(op_exp_curr, rev_curr)
#                     financial_data["efficiency"]["prev"] = calc_eff(op_exp_prev, rev_prev)

#                 except Exception as e:
#                     print(f"⚠️ Calculation Error {ticker}: {e}")

#             # יעדים
#             beta = info.get('beta', 1.5) or 1.5
#             volatility = beta * 0.04
#             financial_data["target_price"] = round(current_price * (1 + (volatility * 2.0)), 2)
#             financial_data["stop_loss"] = round(current_price * (1 - volatility), 2)

#             return financial_data

#         except Exception as e:
#             print(f"⚠️ Data Error {ticker}: {e}")
#             return None

# import finnhub
# import yfinance as yf
# import pandas as pd
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

#     def analyze(self, ticker):
#         try:
#             stock_yf = yf.Ticker(ticker)
#             info = stock_yf.info
#             current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
#             if not current_price: return None

#             description = info.get('longBusinessSummary', '')[:400]

#             # --- ניתוח טכני מורחב ---
#             technical_signal = None # ברירת מחדל: אין איתות
#             trend_status = "מגמה לא ברורה"

#             try:
#                 # היסטוריה של שנה (חשוב ל-SMA150)
#                 hist = stock_yf.history(period="1y")

#                 if len(hist) > 150:
#                     # 1. חישוב ממוצעים
#                     hist['SMA50'] = hist['Close'].rolling(window=50).mean()
#                     hist['SMA150'] = hist['Close'].rolling(window=150).mean()

#                     # נתונים אחרונים
#                     curr_close = hist['Close'].iloc[-1]
#                     curr_open = hist['Open'].iloc[-1]
#                     curr_high = hist['High'].iloc[-1]
#                     curr_low = hist['Low'].iloc[-1]

#                     prev_close = hist['Close'].iloc[-2]
#                     prev_open = hist['Open'].iloc[-2]

#                     curr_sma150 = hist['SMA150'].iloc[-1]
#                     prev_sma150 = hist['SMA150'].iloc[-2]

#                     # --- זיהוי חציית SMA150 (ללא קשר לחדשות) ---
#                     was_below_150 = prev_close < prev_sma150
#                     is_above_150 = curr_close > curr_sma150
#                     # מוודאים שלא ברח (עד 3%)
#                     dist_150 = (curr_close - curr_sma150) / curr_sma150

#                     if was_below_150 and is_above_150 and dist_150 < 0.03:
#                         technical_signal = f"💎 חציית SMA150 נקייה (+{dist_150*100:.1f}%)"
#                         trend_status = "✅ היפוך מגמה ראשי"

#                     # --- זיהוי נרות היפוך (Candlestick Patterns) ---
#                     # אם עדיין אין איתות, נחפש נרות
#                     elif not technical_signal:
#                         # חישוב גוף וצלליות
#                         body = abs(curr_close - curr_open)
#                         upper_wick = curr_high - max(curr_close, curr_open)
#                         lower_wick = min(curr_close, curr_open) - curr_low
#                         total_range = curr_high - curr_low

#                         # א. נר פטיש (Hammer) - היפוך למעלה
#                         # צללית תחתונה ארוכה פי 2 מהגוף, צללית עליונה קטנה
#                         if lower_wick > (body * 2) and upper_wick < (body * 0.5):
#                             technical_signal = "🔨 נר פטיש (Hammer) - פוטנציאל היפוך"

#                         # ב. נר עוטף שורי (Bullish Engulfing)
#                         # אתמול אדום, היום ירוק ועוטף את כל הגוף של אתמול
#                         elif (prev_close < prev_open) and (curr_close > curr_open):
#                             if curr_close > prev_open and curr_open < prev_close:
#                                 technical_signal = "🕯️ נר עוטף שורי (Bullish Engulfing)"

#                         # ג. בדיקת התכנסות (דמוי ידית של ספל)
#                         # המניה קרובה לגבוה שנתי, אבל התנודתיות ירדה ב-5 ימים האחרונים
#                         elif curr_close > (hist['High'].max() * 0.9): # קרוב לשיא
#                             recent_volatility = hist['Close'].pct_change().tail(5).std()
#                             if recent_volatility < 0.015: # תנודתיות נמוכה מאוד
#                                 technical_signal = "☕ התכנסות בשיא (פוטנציאל ספל וידית)"

#             except Exception as e:
#                 print(f"Technical check error: {e}")

#             # --- בניית האובייקט הסופי ---
#             financial_data = {
#                 "current_price": round(current_price, 2),
#                 "market_cap": info.get('marketCap', 0),
#                 "description": description,
#                 "technical_signal": technical_signal, # יכיל מחרוזת רק אם יש איתות
#                 "trend_status": trend_status,
#                 # שאר הנתונים (השארתי ריק לקריאות, הקוד המקורי שלך ממלא אותם)
#                 "revenue": {"curr": 0, "prev": 0, "change": 0},
#                 "net_income": {"curr": 0, "prev": 0, "change": 0},
#                 "efficiency": {"curr": None, "prev": None},
#                 "target_price": 0, "stop_loss": 0
#             }

#             # (כאן אמור להיות המשך הקוד הפיננסי הרגיל שלך שמחשב הכנסות וכו')
#             # ... העתק את הלוגיקה של quarterly_financials מהקובץ הקודם ...

#             return financial_data

#         except Exception as e:
#             return None



# import finnhub
# import yfinance as yf
# import pandas as pd
# from app.core.config import settings

# class FinancialAnalyzer:
#     def __init__(self):
#         self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

#     def analyze(self, ticker):
#         try:
#             stock_yf = yf.Ticker(ticker)
#             info = stock_yf.info
#             current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
#             if not current_price: return None

#             description = info.get('longBusinessSummary', info.get('description', 'תיאור לא זמין'))[:800]

#             # משתנים לאתחול
#             technical_signal = None
#             trend_status = "מגמה לא ברורה"
#             vol_ratio = 1.0

#             # --- ניתוח טכני ---
#             try:
#                 hist = stock_yf.history(period="1y")

#                 if len(hist) > 150:
#                     # ממוצעים
#                     hist['SMA50'] = hist['Close'].rolling(window=50).mean()
#                     hist['SMA150'] = hist['Close'].rolling(window=150).mean()

#                     curr_close = hist['Close'].iloc[-1]
#                     prev_close = hist['Close'].iloc[-2]

#                     curr_sma150 = hist['SMA150'].iloc[-1]
#                     prev_sma150 = hist['SMA150'].iloc[-2]

#                     # ווליום
#                     avg_vol_30 = hist['Volume'].tail(30).mean()
#                     curr_vol = hist['Volume'].iloc[-1]
#                     vol_ratio = round(curr_vol / avg_vol_30, 1) if avg_vol_30 > 0 else 0

#                     # --- הלוגיקה לחציית SMA150 ---
#                     # 1. אתמול מתחת לקו
#                     was_below = prev_close < prev_sma150
#                     # 2. היום מעל הקו
#                     is_above = curr_close > curr_sma150
#                     # 3. מרחק (לא ברח יותר מ-3%)
#                     dist_pct = (curr_close - curr_sma150) / curr_sma150

#                     if was_below and is_above and dist_pct < 0.04:
#                         technical_signal = f"💎 חציית SMA150 טרייה! (+{dist_pct*100:.1f}%)"
#                         trend_status = "✅ התחלת מגמה (מעל SMA150)"

#                     elif curr_close > curr_sma150:
#                         trend_status = "✅ במגמה עולה (מעל SMA150)"
#                         # בדיקת משנה: פריצת SMA50
#                         if prev_close < hist['SMA50'].iloc[-2] and curr_close > hist['SMA50'].iloc[-1]:
#                              technical_signal = f"🔥 פריצת SMA50 (בתוך מגמה עולה)"
#                     else:
#                         trend_status = "⛔ מתחת ל-SMA150 (מגמת ירידה)"

#                     # זיהוי נרות (רק אם אין איתות חזק יותר)
#                     if not technical_signal:
#                         curr_open = hist['Open'].iloc[-1]
#                         # נר עוטף שורי
#                         if (prev_close < hist['Open'].iloc[-2]) and (curr_close > curr_open):
#                              if curr_close > hist['Open'].iloc[-2] and curr_open < prev_close:
#                                 technical_signal = "🕯️ נר עוטף שורי (Bullish Engulfing)"

#             except Exception as e:
#                 print(f"Tech Error {ticker}: {e}")

#             # --- בניית האובייקט הפיננסי ---
#             financial_data = {
#                 "current_price": round(current_price, 2),
#                 "market_cap": info.get('marketCap', 0),
#                 "description": description,
#                 "technical_signal": technical_signal,
#                 "trend_status": trend_status,
#                 "volume_ratio": vol_ratio, # הוספנו את הווליום
#                 "revenue": {"curr": 0, "prev": 0, "change": 0},
#                 "net_income": {"curr": 0, "prev": 0, "change": 0},
#                 "efficiency": {"curr": None, "prev": None},
#                 "target_price": round(current_price * 1.25, 2),
#                 "stop_loss": round(current_price * 0.93, 2)
#             }

#             # --- שליפת נתונים כספיים (QoQ) ---
#             # וודא שהחלק הזה קיים בקובץ שלך!
#             q_fin = stock_yf.quarterly_financials
#             if not q_fin.empty:
#                 try:
#                     def get_val(key, idx):
#                         if key in q_fin.index and len(q_fin.columns) > idx:
#                             return q_fin.loc[key].iloc[idx]
#                         return 0

#                     # הכנסות
#                     r_curr = get_val('Total Revenue', 0) or get_val('Operating Revenue', 0)
#                     r_prev = get_val('Total Revenue', 1) or get_val('Operating Revenue', 1)

#                     if r_prev:
#                         change = ((r_curr - r_prev) / r_prev) * 100
#                         financial_data["revenue"] = {"curr": r_curr, "prev": r_prev, "change": round(change, 2)}

#                     # רווח נקי
#                     n_curr = get_val('Net Income', 0)
#                     n_prev = get_val('Net Income', 1)
#                     if n_prev: # מונע חלוקה באפס
#                         change_ni = ((n_curr - n_prev) / abs(n_prev)) * 100
#                         financial_data["net_income"] = {"curr": n_curr, "prev": n_prev, "change": round(change_ni, 2)}

#                 except Exception as ex:
#                     print(f"Financial calc error: {ex}")

#             return financial_data

#         except Exception as e:
#             print(f"⚠️ Data Error {ticker}: {e}")
#             return None


import finnhub
import yfinance as yf
import pandas as pd
from app.core.config import settings

class FinancialAnalyzer:
    def __init__(self):
        self.client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None

    def analyze(self, ticker):
        try:
            stock_yf = yf.Ticker(ticker)
            info = stock_yf.info
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            if not current_price: return None

            description = info.get('longBusinessSummary', info.get('description', 'תיאור לא זמין'))[:800]

            # משתנים לאתחול
            technical_signal = None
            trend_status = "מגמה לא ברורה"
            vol_ratio = 1.0

            # --- ניתוח טכני ---
            try:
                hist = stock_yf.history(period="1y")

                if len(hist) > 150:
                    hist['SMA50'] = hist['Close'].rolling(window=50).mean()
                    hist['SMA150'] = hist['Close'].rolling(window=150).mean()

                    curr_close = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2]
                    curr_sma150 = hist['SMA150'].iloc[-1]
                    prev_sma150 = hist['SMA150'].iloc[-2]

                    # ווליום
                    avg_vol_30 = hist['Volume'].tail(30).mean()
                    curr_vol = hist['Volume'].iloc[-1]
                    vol_ratio = round(curr_vol / avg_vol_30, 1) if avg_vol_30 > 0 else 0

                    # --- לוגיקה לחציית SMA150 ---
                    was_below = prev_close < prev_sma150
                    is_above = curr_close > curr_sma150
                    dist_pct = (curr_close - curr_sma150) / curr_sma150

                    if was_below and is_above and dist_pct < 0.04:
                        technical_signal = f"💎 חציית SMA150 טרייה! (+{dist_pct*100:.1f}%)"
                        trend_status = "✅ התחלת מגמה (מעל SMA150)"

                    elif curr_close > curr_sma150:
                        trend_status = "✅ במגמה עולה (מעל SMA150)"
                        if prev_close < hist['SMA50'].iloc[-2] and curr_close > hist['SMA50'].iloc[-1]:
                             technical_signal = f"🔥 פריצת SMA50 (בתוך מגמה עולה)"
                    else:
                        trend_status = "⛔ מתחת ל-SMA150 (מגמת ירידה)"

                    if not technical_signal:
                        curr_open = hist['Open'].iloc[-1]
                        if (prev_close < hist['Open'].iloc[-2]) and (curr_close > curr_open):
                             if curr_close > hist['Open'].iloc[-2] and curr_open < prev_close:
                                technical_signal = "🕯️ נר עוטף שורי (Bullish Engulfing)"

            except Exception as e:
                print(f"Tech Error {ticker}: {e}")

            # --- בניית האובייקט הפיננסי ---
            financial_data = {
                "current_price": round(current_price, 2),
                "market_cap": info.get('marketCap', 0),
                "description": description,
                "technical_signal": technical_signal,
                "trend_status": trend_status,
                "volume_ratio": vol_ratio,
                "revenue": {"curr": 0, "prev": 0, "change": 0},
                "net_income": {"curr": 0, "prev": 0, "change": 0},
                "efficiency": {"curr": None, "prev": None}, # הנה זה
                "target_price": round(current_price * 1.25, 2),
                "stop_loss": round(current_price * 0.93, 2)
            }

            # --- חישוב פיננסי + התייעלות ---
            q_fin = stock_yf.quarterly_financials
            if not q_fin.empty:
                try:
                    def get_val(key, idx):
                        if key in q_fin.index and len(q_fin.columns) > idx:
                            return q_fin.loc[key].iloc[idx]
                        return 0

                    # 1. הכנסות
                    r_curr = get_val('Total Revenue', 0) or get_val('Operating Revenue', 0)
                    r_prev = get_val('Total Revenue', 1) or get_val('Operating Revenue', 1)
                    if r_prev:
                        change = ((r_curr - r_prev) / r_prev) * 100
                        financial_data["revenue"] = {"curr": r_curr, "prev": r_prev, "change": round(change, 2)}

                    # 2. רווח נקי
                    n_curr = get_val('Net Income', 0)
                    n_prev = get_val('Net Income', 1)
                    if n_prev:
                        change_ni = ((n_curr - n_prev) / abs(n_prev)) * 100
                        financial_data["net_income"] = {"curr": n_curr, "prev": n_prev, "change": round(change_ni, 2)}

                    # 3. התייעלות (Efficiency) - החדש!
                    # משיכת הוצאות תפעול
                    op_exp_curr = get_val('Total Operating Expenses', 0)
                    op_exp_prev = get_val('Total Operating Expenses', 1)

                    # אם לא קיים שדה ישיר, נחשב: הכנסות פחות רווח תפעולי
                    if op_exp_curr == 0: op_exp_curr = r_curr - get_val('Operating Income', 0)
                    if op_exp_prev == 0: op_exp_prev = r_prev - get_val('Operating Income', 1)

                    def calc_eff(exp, rev):
                        if rev and rev != 0: return round((exp / rev) * 100, 2)
                        return None

                    financial_data["efficiency"]["curr"] = calc_eff(op_exp_curr, r_curr)
                    financial_data["efficiency"]["prev"] = calc_eff(op_exp_prev, r_prev)

                except Exception as ex:
                    print(f"Financial calc error: {ex}")

            return financial_data

        except Exception as e:
            print(f"⚠️ Data Error {ticker}: {e}")
            return None