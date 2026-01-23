# import sys
# import os
# from datetime import datetime, timezone
# import time

# # הוספת נתיב העבודה
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from app.core.db import SessionLocal, init_db, engine
# from app.models.models import AlertHistory
# from app.services.screener_service import ScreenerService
# from app.services.data_fetcher import DataFetcher
# from app.ta.engine import TAEngine
# from app.services.email_service import EmailService
# from app.services.ai_service import AIService

# def run_scan():
#     print("📦 Establishing database connection...")
#     try:
#         # from app.core.db import Base, engine
#         # Base.metadata.drop_all(bind=engine) # מוחק הכל
#         init_db()
#         db = SessionLocal()
#         print("✅ Database ready.")
#     except Exception as e:
#         print(f"❌ Database error: {e}")
#         return

#     print("🚀 Starting Professional AI Scan...")

#     try:
#         # 1. קבלת רשימת מניות מהסורק
#         potential_stocks = ScreenerService.get_candidates()

#         if not potential_stocks:
#             print("❌ No candidates found.")
#             return

#         found_alerts = []

#         # 2. מעבר על כל מניה וניתוח עומק
#         for ticker in potential_stocks:
#             print(f"\n--- 🔍 Deep Analysis: {ticker} ---")
#             time.sleep(2)

#             try:
#                 # א. נתונים טכניים (yfinance)
#                 data = DataFetcher.get_stock_data(ticker)
#                 if data is None or data.empty:
#                     continue

#                 # ב. הרצת מנוע טכני (MA20/50, RSI, Vol)
#                 engine_ta = TAEngine(ticker, data)
#                 analysis = engine_ta.analyze()
#                 if not analysis: continue

#                 score = analysis.get('score', 0)
#                 print(f"📊 Technical Score: {score}/5")

#                 # ג. סינון ראשוני (רק ציונים טובים עוברים ל-AI כדי לחסוך בעלויות)
#                 if score >= 2:
#                     # בדיקה אם כבר נשלח היום
#                     today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
#                     already_sent = db.query(AlertHistory).filter(
#                         AlertHistory.ticker == ticker,
#                         AlertHistory.timestamp >= today_start
#                     ).first()

#                     if not already_sent:
#                         print(f"🤖 Generating AI Report for {ticker}...")

#                         # ד. משיכת נתונים מ-Finnhub (פונדמנטלי + חדשות)
#                         fundamentals = DataFetcher.get_finnhub_fundamentals(ticker)
#                         news = DataFetcher.get_finnhub_news(ticker)

#                         # ה. ניתוח AI בעברית
#                         ai_report = AIService.analyze_stock(
#                             ticker=ticker,
#                             price=analysis['price'],
#                             score=score,
#                             reasons=analysis['reasons'],
#                             fundamentals=fundamentals,
#                             news=news
#                         )

#                         analysis['ai_report'] = ai_report

#                         # ו. שמירה ל-DB
#                         new_alert = AlertHistory(
#                             ticker=ticker,
#                             price=float(analysis['price']),
#                             signal_type=f"AI_SCORE_{score}",
#                             reasons=", ".join(analysis['reasons'])
#                         )
#                         db.add(new_alert)
#                         db.commit()

#                         found_alerts.append(analysis)
#                     else:
#                         print(f"ℹ️ {ticker} already processed today.")

#             except Exception as e:
#                 print(f"⚠️ Error with {ticker}: {e}")
#                 db.rollback()
#                 continue

#         # 3. שליחת הדוח המעוצב
#         if found_alerts:
#             print(f"\n📧 Sending AI-Powered report for {len(found_alerts)} stocks...")
#             EmailService.send_daily_report(found_alerts)
#         else:
#             print("\n😴 No quality setups found today.")

#     except Exception as e:
#         print(f"❌ Critical error: {e}")
#     finally:
#         db.close()
#         print("\n✅ Scan complete.")

# if __name__ == "__main__":
#     run_scan()



import sys
import os
from datetime import datetime, timezone
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import SessionLocal, init_db
from app.models.models import AlertHistory
from app.services.screener_service import ScreenerService
from app.services.data_fetcher import DataFetcher
from app.ta.engine import TAEngine
from app.services.email_service import EmailService
from app.services.ai_service import AIService

def run_scan():
    print("🚀 Starting Professional AI Scan...")
    init_db()
    db = SessionLocal()

    try:
        potential_stocks = ScreenerService.get_candidates()
        # potential_stocks= [ "IBM" ]
        if not potential_stocks:
            print("❌ No candidates found.")
            return

        found_alerts = []

        for ticker in potential_stocks:
            print(f"\n--- 🔍 Deep Analysis: {ticker} ---")
            time.sleep(1) # מניעת חסימה מ-APIs

            try:
                data = DataFetcher.get_stock_data(ticker)
                if data is None or data.empty: continue

                engine_ta = TAEngine(ticker, data)
                analysis = engine_ta.analyze()
                if not analysis: continue

                score = analysis.get('score', 0)

                # רק מניות עם ציון טוב עוברות לניתוח AI מלא
                if score >= 0:
                    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    already_sent = db.query(AlertHistory).filter(
                        AlertHistory.ticker == ticker,
                        AlertHistory.timestamp >= today_start
                    ).first()

                    if not already_sent:
                        print(f"🤖 Fetching Profile & Generating AI Report for {ticker}...")

                        # משיכת פרופיל חברה, פונדמנטל וחדשות
                        company_info = DataFetcher.get_company_profile(ticker)
                        fundamentals = DataFetcher.get_finnhub_fundamentals(ticker)
                        news = DataFetcher.get_finnhub_news(ticker)

                        ai_report = AIService.analyze_stock(
                            ticker=ticker,
                            price=analysis['price'],
                            score=score,
                            reasons=analysis['reasons'],
                            fundamentals=fundamentals,
                            news=news,
                            company_info=company_info
                        )

                        analysis['ai_report'] = ai_report
                        analysis['company_name'] = company_info.get('name', ticker)
                        analysis['industry'] = company_info.get('industry', 'N/A')

                        # שמירה ל-DB
                        new_alert = AlertHistory(
                            ticker=ticker,
                            price=float(analysis['price']),
                            signal_type=f"AI_SCORE_{score}",
                            reasons=", ".join(analysis['reasons'])
                        )
                        db.add(new_alert)
                        db.commit()

                        found_alerts.append(analysis)

            except Exception as e:
                print(f"⚠️ Error with {ticker}: {e}")
                db.rollback()

        if found_alerts:
            EmailService.send_daily_report(found_alerts)
        else:
            print("\n😴 No quality setups found today.")

    finally:
        db.close()
        print("\n✅ Scan complete.")


if __name__ == "__main__":
    print("Script run")
    run_scan()
