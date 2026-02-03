# import time
# from app.services.screener_service import ScreenerService
# from app.services.news_scraper import NewsScraper
# from app.services.news_model import NewsModel
# from app.services.financial_service import FinancialAnalyzer
# from app.services.email_service import EmailService
# from app.data.mongo_client import MongoDB

# # ה-URL שלך מ-Finviz (דוגמה)
# FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_mid,sh_avgvol_o500,sh_short_o10,ta_perf2_1w10o&ft=4"

# # ... (imports נשארים אותו דבר)

# def run_news_driven_scan():
#     print("🚀 Starting Scan (Hybrid Free Mode)...")

#     # 1. שליפת מועמדים
#     tickers = ScreenerService.get_candidates_from_url(FINVIZ_SCREENER_URL)

#     # ניהול רשימת המניות (אם הסורק נכשל, הוא מחזיר רשימת גיבוי שראית בלוג)
#     if not tickers:
#         print("📭 No tickers found.")
#         return

#     scraper = NewsScraper()
#     model = NewsModel()
#     fin_analyzer = FinancialAnalyzer()

#     opportunities = []

#     for ticker in tickers:
#         print(f"🔎 Checking {ticker}...")

#         # א. משיכת חדשות
#         stats, news_items = scraper.get_stock_data(ticker)
#         if not news_items: continue

#         # שמירה ל-DB
#         for item in news_items:
#             MongoDB.save_news_event(ticker, item)

#         # ב. דירוג טקסט (AI Model)
#         best_text_score = 0
#         best_headline = ""
#         for item in news_items:
#             score = model.predict_impact(item['headline'])
#             if score > best_text_score:
#                 best_text_score = score
#                 best_headline = item['headline']

#         # ג. בדיקת איכות
#         # הורדתי את הרף ל-60 כדי שתראה תוצאות בהתחלה
#         if best_text_score >= 60:
#             print(f"   🔥 Signal Found ({best_text_score}): {best_headline}")

#             # שליפת נתונים פיננסיים (הגרסה המתוקנת)
#             fin_data = fin_analyzer.analyze(ticker)

#             if fin_data:
#                 opportunities.append({
#                     "ticker": ticker,
#                     "headline": best_headline,
#                     "score": best_text_score, # הציון מבוסס עכשיו רק על הטקסט
#                     "ml_score": best_text_score,
#                     "finnhub_sentiment": 50, # ברירת מחדל
#                     "price": fin_data['current_price'],
#                     "financials": fin_data
#                 })

#         time.sleep(1)

#     # 4. דיווח
#     if opportunities:
#         opportunities.sort(key=lambda x: x['score'], reverse=True)
#         print(f"🎯 Sending report with {len(opportunities)} opportunities.")
#         EmailService.send_report(opportunities)
#     else:
#         print("💤 No high-probability signals today.")

# if __name__ == "__main__":
#     run_news_driven_scan()



# import time
# from app.services.screener_service import ScreenerService
# from app.services.news_scraper import NewsScraper
# from app.services.news_model import NewsModel
# from app.services.financial_service import FinancialAnalyzer
# from app.services.email_service import EmailService
# from app.services.ai_service import AIService # הוספנו את זה
# from app.data.mongo_client import MongoDB

# # FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_smallover,sh_avgvol_o500,ta_rsi_nos50&ft=4"
# FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=211&f=cap_midover%2Cfa_debteq_u1%2Cfa_roe_o20%2Csh_avgvol_o200%2Cta_beta_o1%2Cta_change_u%2Cta_highlow50d_nh%2Cta_sma200_pa%2Cta_sma50_pa&ft=4"
# # FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_smallover%2Csh_avgvol_o500%2Csh_short_o10%2Cta_beta_o1.5%2Cta_change_u%2Cta_perf2_1w10o%2Cta_sma20_pa&ft=4"

# def run_news_driven_scan():
#     print("🚀 Starting AI-Powered Scan...")

#     tickers = ScreenerService.get_candidates_from_url(FINVIZ_SCREENER_URL)

#     if not tickers:
#         print("📭 No tickers found.")
#         return

#     scraper = NewsScraper()
#     model = NewsModel()
#     fin_analyzer = FinancialAnalyzer()
#     ai_service = AIService() # אתחול ה-AI

#     opportunities = []

#     for ticker in tickers:
#         print(f"🔎 Analyzing {ticker}...")

#         # 1. חדשות
#         stats, news_items = scraper.get_stock_data(ticker)
#         if not news_items: continue

#         for item in news_items:
#             MongoDB.save_news_event(ticker, item)

#         # 2. סינון חדשות
#         best_text_score = 0
#         best_headline = ""
#         for item in news_items:
#             score = model.predict_impact(item['headline'])
#             if score > best_text_score:
#                 best_text_score = score
#                 best_headline = item['headline']

#         # סף סינון (הורדתי ל-60 כדי שתראה תוצאות)
#         if best_text_score >= 70:
#             print(f"   🔥 Signal ({best_text_score}): {best_headline}")

#             # 3. ניתוח פיננסי מעמיק (yfinance)
#             fin_data = fin_analyzer.analyze(ticker)

#             # ... (Imports אותו דבר)

# # בתוך הלולאה, בחלק של ה-AI:

#             if fin_data:
#                 print(f"   🤖 Generating AI Analysis for {ticker}...")

#                 # קריאה ל-AI (מחזיר עכשיו שני חלקים)
#                 ai_result = ai_service.analyze_stock(ticker, best_headline, fin_data)

#                 opportunities.append({
#                     "ticker": ticker,
#                     "headline": best_headline,
#                     "score": best_text_score,
#                     "price": fin_data['current_price'],
#                     "financials": fin_data,
#                     # הזרקת התוצאות מה-AI
#                     "ai_hebrew_desc": ai_result['hebrew_desc'],
#                     "ai_analysis": ai_result['analysis']
#                 })

#         time.sleep(1)

#     if opportunities:
#         opportunities.sort(key=lambda x: x['score'], reverse=True)
#         print(f"🎯 Sending report with {len(opportunities)} AI-analyzed stocks.")
#         EmailService.send_report(opportunities)
#     else:
#         print("💤 No opportunities found.")

# if __name__ == "__main__":
#     run_news_driven_scan()



# import time
# from app.services.screener_service import ScreenerService
# from app.services.news_scraper import NewsScraper
# from app.services.news_model import NewsModel
# from app.services.financial_service import FinancialAnalyzer
# from app.services.email_service import EmailService
# from app.services.ai_service import AIService
# from app.services.news_aggregator import NewsAggregator # הוספנו את זה
# from app.data.mongo_client import MongoDB

# # הלינק הספציפי שלך ל-Finviz
# # FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=211&f=cap_midover%2Cfa_debteq_u1%2Cfa_roe_o20%2Csh_avgvol_o200%2Cta_beta_o1%2Cta_change_u%2Cta_highlow50d_nh%2Cta_sma200_pa%2Cta_sma50_pa&ft=4"
# FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=211&f=cap_smallover,fa_debteq_u1,fa_roe_o15,sh_avgvol_o300,sh_relvol_o1.5,sh_short_o5,ta_change_u,ta_rsi_nos50&ft=4"

# def run_news_driven_scan():
#     print("🚀 Starting Hybrid Scan (Finviz Stocks + RSS News)...")

#     # --- חלק 1: איסוף חדשות כלליות (RSS) ---
#     # זה החלק החדש שמביא כותרות FDA, מיזוגים וכו'
#     news_aggregator = NewsAggregator()
#     general_news = news_aggregator.fetch_last_24h_news()

#     # שמירת החדשות הכלליות ל-DB (בשביל Train Model בעתיד)
#     print("💾 Saving general news to database...")
#     for news in general_news:
#         ticker = news.get('ticker') or "GENERAL"
#         MongoDB.save_news_event(ticker, {
#             'headline': news['headline'],
#             'url': news['url']
#         })

#     # --- חלק 2: סריקת המניות שלך מ-Finviz ---
#     # שימוש בלינק שלך
#     tickers = ScreenerService.get_candidates_from_url(FINVIZ_SCREENER_URL)

#     stock_opportunities = []

#     if tickers:
#         scraper = NewsScraper()
#         model = NewsModel()
#         fin_analyzer = FinancialAnalyzer()
#         ai_service = AIService()

#         for ticker in tickers:
#             print(f"🔎 Analyzing {ticker}...")

#             # 1. משיכת חדשות ספציפיות למניה
#             stats, news_items = scraper.get_stock_data(ticker)
#             if not news_items: continue

#             # שמירה ל-DB
#             for item in news_items:
#                 MongoDB.save_news_event(ticker, item)

#             # 2. סינון ודירוג חדשות
#             best_text_score = 0
#             best_headline = ""
#             for item in news_items:
#                 score = model.predict_impact(item['headline'])
#                 if score > best_text_score:
#                     best_text_score = score
#                     best_headline = item['headline']

#             # סף סינון (70 ומעלה)
#             if best_text_score >= 70:
#                 print(f"   🔥 Signal ({best_text_score}): {best_headline}")

#                 # 3. ניתוח פיננסי
#                 fin_data = fin_analyzer.analyze(ticker)

#                 if fin_data:
#                     print(f"   🤖 Generating AI Analysis for {ticker}...")

#                     # 4. ניתוח AI
#                     ai_result = ai_service.analyze_stock(ticker, best_headline, fin_data)

#                     stock_opportunities.append({
#                         "ticker": ticker,
#                         "headline": best_headline,
#                         "score": best_text_score,
#                         "price": fin_data['current_price'],
#                         "financials": fin_data,
#                         "ai_hebrew_desc": ai_result['hebrew_desc'],
#                         "ai_analysis": ai_result['analysis']
#                     })

#             time.sleep(1) # המתנה קצרה למניעת חסימות

#     # --- חלק 3: שליחת הדוח המשולב ---
#     # בודקים אם יש משהו לשלוח (או מניות או חדשות כלליות)
#     if stock_opportunities or general_news:
#         if stock_opportunities:
#             stock_opportunities.sort(key=lambda x: x['score'], reverse=True)

#         print(f"🎯 Sending report: {len(stock_opportunities)} Stocks & {len(general_news)} Headlines.")

#         # שולחים את שניהם למייל
#         EmailService.send_report(stock_opportunities, general_news)
#     else:
#         print("💤 No significant data found today.")

# if __name__ == "__main__":
#     run_news_driven_scan()


# import time
# from app.services.screener_service import ScreenerService
# from app.services.news_scraper import NewsScraper
# from app.services.news_model import NewsModel
# from app.services.financial_service import FinancialAnalyzer
# from app.services.email_service import EmailService
# from app.services.ai_service import AIService
# from app.services.news_aggregator import NewsAggregator
# from app.data.mongo_client import MongoDB

# # הלינק הטכני שלך (Finviz)
# # FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_smallover,sh_avgvol_o300,ta_sma50_crossabove,ta_rsi_nos50&ft=4"
# # FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=211&f=cap_smallover%2Csh_avgvol_o400%2Csh_relvol_o1.5%2Cta_rsi_nos50&ft=4"
# FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=211&f=cap_smallover,fa_debteq_u1,fa_roe_o15,sh_avgvol_o300,sh_relvol_o1.5,sh_short_o5,ta_change_u,ta_rsi_nos50&ft=4"
# # לינק רחב יותר שמאפשר לבוט למצוא חציות של 150
# # FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_smallover,sh_avgvol_o300,ta_sma20_sa50&ft=4"

# def run_news_driven_scan():
#     print("🚀 Starting Super-Scan (Technical + Biotech News)...")

#     news_aggregator = NewsAggregator()

#     # 1. איסוף כותרות כלליות למייל (RSS)
#     general_news = news_aggregator.fetch_last_24h_news()

#     # שמירה ל-DB
#     for news in general_news:
#         ticker = news.get('ticker') or "GENERAL"
#         MongoDB.save_news_event(ticker, {'headline': news['headline'], 'url': news['url']})

#     # 2. איסוף רשימת המניות לניתוח
#     target_tickers = set() # שימוש ב-Set מונע כפילויות

#     # א' - מניות טכניות מ-Finviz
#     finviz_tickers = ScreenerService.get_candidates_from_url(FINVIZ_SCREENER_URL)
#     if finviz_tickers:
#         print(f"📈 Found {len(finviz_tickers)} Technical Breakout candidates.")
#         target_tickers.update(finviz_tickers)

#     # ב' - מניות ביוטק עם חדשות (התוספת החדשה!)
#     biotech_tickers = news_aggregator.find_biotech_opportunities()
#     if biotech_tickers:
#         print(f"🧬 Adding {len(biotech_tickers)} Biotech Stocks due to FDA/Trial news.")
#         target_tickers.update(biotech_tickers)

#     # המרה חזרה לרשימה
#     final_tickers_list = list(target_tickers)

#     if not final_tickers_list:
#         print("📭 No candidates found today.")
#         return

#     # 3. תהליך הניתוח הרגיל (עובר על כל הרשימה המאוחדת)
#     stock_opportunities = []

#     scraper = NewsScraper()
#     model = NewsModel()
#     fin_analyzer = FinancialAnalyzer()
#     ai_service = AIService()

#     for ticker in final_tickers_list:
#         print(f"🔎 Analyzing {ticker}...")

#         # 1. חדשות
#         stats, news_items = scraper.get_stock_data(ticker)
#         if not news_items:
#             print(f"   Skipping {ticker} (No recent specific news found).")
#             continue

#         for item in news_items:
#             MongoDB.save_news_event(ticker, item)

#         # 2. דירוג
#         best_text_score = 0
#         best_headline = ""
#         for item in news_items:
#             score = model.predict_impact(item['headline'])
#             if score > best_text_score:
#                 best_text_score = score
#                 best_headline = item['headline']

#         # סף סינון (מניות ביוטק לרוב יקבלו ציון גבוה בגלל מילות המפתח)
#         if best_text_score >= 60:
#             print(f"   🔥 Signal ({best_text_score}): {best_headline}")

#             # 3. פיננסי + טכני
#             fin_data = fin_analyzer.analyze(ticker)

#             if fin_data:
#                 print(f"   🤖 AI Analysis for {ticker}...")
#                 ai_result = ai_service.analyze_stock(ticker, best_headline, fin_data)

#                 stock_opportunities.append({
#                     "ticker": ticker,
#                     "headline": best_headline,
#                     "score": best_text_score,
#                     "price": fin_data['current_price'],
#                     "financials": fin_data,
#                     "ai_hebrew_desc": ai_result['hebrew_desc'],
#                     "ai_analysis": ai_result['analysis']
#                 })

#         time.sleep(1)

#     # 4. שליחת דוח
#     if stock_opportunities or general_news:
#         stock_opportunities.sort(key=lambda x: x['score'], reverse=True)
#         print(f"🎯 Sending report: {len(stock_opportunities)} Stocks & {len(general_news)} Headlines.")
#         EmailService.send_report(stock_opportunities, general_news)
#     else:
#         print("💤 No significant opportunities found.")

# if __name__ == "__main__":
#     run_news_driven_scan()


# import time
# from app.services.screener_service import ScreenerService
# from app.services.news_scraper import NewsScraper
# from app.services.news_model import NewsModel
# from app.services.financial_service import FinancialAnalyzer
# from app.services.email_service import EmailService
# from app.services.ai_service import AIService
# from app.services.news_aggregator import NewsAggregator
# from app.data.mongo_client import MongoDB

# # לינק שמאפשר למצוא גם תבניות טכניות (מרחיב את היריעה)
# FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_smallover,sh_avgvol_o300,ta_sma20_sa50&ft=4"

# def run_hybrid_scan():
#     print("🚀 Starting Hybrid Scan (News + Pure Technicals)...")

#     # 1. RSS כללי
#     news_aggregator = NewsAggregator()
#     general_news = news_aggregator.fetch_last_24h_news()

#     # 2. איסוף מניות
#     target_tickers = set()

#     # א' - פינביז (הבסיס)
#     finviz_tickers = ScreenerService.get_candidates_from_url(FINVIZ_SCREENER_URL)
#     if finviz_tickers:
#         print(f"📈 Scanned {len(finviz_tickers)} charts from Finviz.")
#         target_tickers.update(finviz_tickers)

#     # ב' - ביוטק
#     biotech_tickers = news_aggregator.find_biotech_opportunities()
#     if biotech_tickers:
#         target_tickers.update(biotech_tickers)

#     final_tickers_list = list(target_tickers)
#     stock_opportunities = []

#     scraper = NewsScraper()
#     model = NewsModel()
#     fin_analyzer = FinancialAnalyzer()
#     ai_service = AIService()

#     print(f"🔎 Deep analyzing {len(final_tickers_list)} candidates...")

#     for ticker in final_tickers_list:
#         # 1. קודם כל - ניתוח פיננסי וטכני
#         # אנחנו עושים את זה *לפני* החדשות, כי אולי זה טכני טהור
#         fin_data = fin_analyzer.analyze(ticker)

#         if not fin_data:
#             continue

#         technical_signal = fin_data.get('technical_signal')

#         # 2. בדיקת חדשות
#         stats, news_items = scraper.get_stock_data(ticker)

#         # חישוב ציון חדשות (אם יש)
#         news_score = 0
#         best_headline = "ללא חדשות טריות (איתות טכני בלבד)"

#         if news_items:
#             for item in news_items:
#                 MongoDB.save_news_event(ticker, item) # שמירה ללמידה
#                 score = model.predict_impact(item['headline'])
#                 if score > news_score:
#                     news_score = score
#                     best_headline = item['headline']

#         # --- עכשיו ההחלטה: האם להוסיף את המניה? ---

#         should_add = False
#         reason = ""

#         # מסלול א': יש חדשות חזקות
#         if news_score >= 60:
#             should_add = True
#             reason = "News"

#         # מסלול ב': אין חדשות, אבל יש איתות טכני חזק (הבקשה שלך!)
#         elif technical_signal is not None:
#             should_add = True
#             reason = "Technical"
#             # ניתן ציון מלאכותי כדי שיופיע בדוח, אבל נמוך יותר מחדשות לוהטות
#             news_score = 55

#         if should_add:
#             print(f"   ✅ Found Opportunity: {ticker} | Reason: {reason}")
#             if reason == "Technical":
#                 print(f"      Signal: {technical_signal}")

#             # אם זה טכני בלבד, אין צורך ב-AI כבד לניתוח טקסט, נחסוך זמן
#             ai_analysis_text = "איתות טכני טהור. המערכת זיהתה תבנית מחיר משמעותית ללא חדשות ישירות."
#             if reason == "News":
#                  ai_res = ai_service.analyze_stock(ticker, best_headline, fin_data)
#                  ai_analysis_text = ai_res['analysis']

#             stock_opportunities.append({
#                 "ticker": ticker,
#                 "headline": best_headline,
#                 "score": news_score,
#                 "price": fin_data['current_price'],
#                 "financials": fin_data,
#                 "ai_hebrew_desc": "הזדמנות מסחר", # אפשר לשפר עם AI אם רוצים
#                 "ai_analysis": ai_analysis_text
#             })

#         time.sleep(1)

#     # 4. שליחת דוח
#     if stock_opportunities or general_news:
#         stock_opportunities.sort(key=lambda x: x['score'], reverse=True)
#         EmailService.send_report(stock_opportunities, general_news)
#         print("Done.")
#     else:
#         print("No opportunities.")

# if __name__ == "__main__":
#     run_hybrid_scan()


# import time
# from app.services.screener_service import ScreenerService
# from app.services.news_scraper import NewsScraper
# from app.services.news_model import NewsModel
# from app.services.financial_service import FinancialAnalyzer
# from app.services.email_service import EmailService
# from app.services.ai_service import AIService
# from app.services.news_aggregator import NewsAggregator
# from app.data.mongo_client import MongoDB

# # לינק רחב יותר כדי לתפוס את ה-150
# FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_smallover,sh_avgvol_o300,ta_sma20_sa50&ft=4"

# def run_hybrid_scan():
#     print("🚀 Starting FULL Hybrid Scan...")

#     news_aggregator = NewsAggregator()
#     general_news = news_aggregator.fetch_last_24h_news()

#     target_tickers = set()

#     # 1. איסוף מפינביז
#     finviz_tickers = ScreenerService.get_candidates_from_url(FINVIZ_SCREENER_URL)
#     if finviz_tickers:
#         print(f"📈 Candidates from Finviz: {len(finviz_tickers)}")
#         target_tickers.update(finviz_tickers)

#     # 2. איסוף מביוטק
#     biotech_tickers = news_aggregator.find_biotech_opportunities()
#     if biotech_tickers:
#         target_tickers.update(biotech_tickers)

#     final_tickers_list = list(target_tickers)
#     stock_opportunities = []

#     scraper = NewsScraper()
#     model = NewsModel()
#     fin_analyzer = FinancialAnalyzer()
#     ai_service = AIService() # חובה שיהיה מוגדר

#     print(f"🔎 Analyzing {len(final_tickers_list)} stocks...")

#     for ticker in final_tickers_list:
#         # א. ניתוח פיננסי מלא (כולל QoQ ו-SMA150)
#         fin_data = fin_analyzer.analyze(ticker)
#         if not fin_data: continue

#         technical_signal = fin_data.get('technical_signal')

#         # ב. בדיקת חדשות
#         stats, news_items = scraper.get_stock_data(ticker)
#         news_score = 0
#         best_headline = "איתות טכני: " + (technical_signal if technical_signal else "ללא חדשות")

#         real_headline_found = False
#         if news_items:
#             for item in news_items:
#                 MongoDB.save_news_event(ticker, item)
#                 score = model.predict_impact(item['headline'])
#                 if score > news_score:
#                     news_score = score
#                     best_headline = item['headline']
#                     real_headline_found = True

#         # ג. קבלת החלטה
#         should_add = False
#         reason = ""

#         if news_score >= 60:
#             should_add = True
#             reason = "News"
#         elif technical_signal is not None:
#             should_add = True
#             reason = "Technical"
#             if not real_headline_found:
#                 news_score = 55 # ציון מלאכותי כדי שייכנס לטבלה

#         if should_add:
#             print(f"   ✅ Found {ticker} ({reason})")

#             # ד. הפעלת AI - חובה גם לטכני כדי לקבל תיאור חברה!
#             # אם אין כותרת אמיתית, נשלח ל-AI את האיתות הטכני כ"כותרת" לניתוח
#             prompt_headline = best_headline
#             if reason == "Technical" and not real_headline_found:
#                 prompt_headline = f"Technical Signal: {technical_signal}. Company analysis needed."

#             ai_result = ai_service.analyze_stock(ticker, prompt_headline, fin_data)

#             stock_opportunities.append({
#                 "ticker": ticker,
#                 "headline": best_headline,
#                 "score": news_score,
#                 "price": fin_data['current_price'],
#                 "financials": fin_data, # מכיל עכשיו את כל ה-QoQ
#                 "ai_hebrew_desc": ai_result['hebrew_desc'], # התיאור בעברית
#                 "ai_analysis": ai_result['analysis']
#             })

#         time.sleep(1)

#     if stock_opportunities or general_news:
#         stock_opportunities.sort(key=lambda x: x['score'], reverse=True)
#         EmailService.send_report(stock_opportunities, general_news)
#         print("Done.")
#     else:
#         print("No opportunities found.")

# if __name__ == "__main__":
#     run_hybrid_scan()



import time
from app.services.screener_service import ScreenerService
from app.services.news_scraper import NewsScraper
from app.services.news_model import NewsModel
from app.services.financial_service import FinancialAnalyzer
from app.services.email_service import EmailService
from app.services.ai_service import AIService
from app.services.news_aggregator import NewsAggregator
from app.data.mongo_client import MongoDB

# לינק רחב יותר כדי לתפוס את ה-150
FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=cap_smallover,sh_avgvol_o300,ta_sma20_sa50&ft=4"

def run_hybrid_scan():
    print("🚀 Starting Hybrid Scan (With Smart Filter)...")

    news_aggregator = NewsAggregator()
    general_news = news_aggregator.fetch_last_24h_news()

    target_tickers = set()

    # 1. איסוף מפינביז
    finviz_tickers = ScreenerService.get_candidates_from_url(FINVIZ_SCREENER_URL)
    if finviz_tickers:
        print(f"📈 Candidates from Finviz: {len(finviz_tickers)}")
        target_tickers.update(finviz_tickers)

    # 2. איסוף מביוטק
    biotech_tickers = news_aggregator.find_biotech_opportunities()
    if biotech_tickers:
        target_tickers.update(biotech_tickers)

    final_tickers_list = list(target_tickers)
    stock_opportunities = []

    scraper = NewsScraper()
    model = NewsModel()
    fin_analyzer = FinancialAnalyzer()
    ai_service = AIService()

    print(f"🔎 Analyzing {len(final_tickers_list)} stocks...")

    for ticker in final_tickers_list:

        # --- סינון חדש: האם כבר שלחנו את זה לאחרונה? ---
        if MongoDB.was_sent_recently(ticker, days=3):
            print(f"   ⏭️ Skipping {ticker} (Sent in last 3 days).")
            continue
        # -----------------------------------------------

        # א. ניתוח פיננסי מלא
        fin_data = fin_analyzer.analyze(ticker)
        if not fin_data: continue

        technical_signal = fin_data.get('technical_signal')

        # ב. בדיקת חדשות
        stats, news_items = scraper.get_stock_data(ticker)
        news_score = 0
        best_headline = "איתות טכני: " + (technical_signal if technical_signal else "ללא חדשות")

        real_headline_found = False
        if news_items:
            for item in news_items:
                MongoDB.save_news_event(ticker, item)
                score = model.predict_impact(item['headline'])
                if score > news_score:
                    news_score = score
                    best_headline = item['headline']
                    real_headline_found = True

        # ג. קבלת החלטה
        should_add = False
        reason = ""

        if news_score >= 60:
            should_add = True
            reason = "News"
        elif technical_signal is not None:
            should_add = True
            reason = "Technical"
            if not real_headline_found:
                news_score = 55 # ציון מלאכותי

        if should_add:
            print(f"   ✅ Found {ticker} ({reason})")

            # --- תיעוד חדש: שומרים ששלחנו את המניה ---
            MongoDB.log_sent_alert(ticker, reason)
            # -----------------------------------------

            # ד. הפעלת AI
            prompt_headline = best_headline
            if reason == "Technical" and not real_headline_found:
                prompt_headline = f"Technical Signal: {technical_signal}. Company analysis needed."

            ai_result = ai_service.analyze_stock(ticker, prompt_headline, fin_data)

            stock_opportunities.append({
                "ticker": ticker,
                "headline": best_headline,
                "score": news_score,
                "price": fin_data['current_price'],
                "financials": fin_data,
                "ai_hebrew_desc": ai_result['hebrew_desc'],
                "ai_analysis": ai_result['analysis']
            })

        time.sleep(1)

    if stock_opportunities or general_news:
        stock_opportunities.sort(key=lambda x: x['score'], reverse=True)
        EmailService.send_report(stock_opportunities, general_news)
        print("Done.")
    else:
        print("No NEW opportunities found (Spam filter active).")

if __name__ == "__main__":
    run_hybrid_scan()