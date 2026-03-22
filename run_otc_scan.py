import time
from app.services.tradingview_service import TradingViewService
from app.services.otc_scanner import OTCScanner
from app.services.email_service import EmailService
from app.services.ai_service import AIService
from app.data.mongo_client import MongoDB

# ניתן להשתמש ב-TradingView כדי לשלוף רשימה ראשונית של מניות Penny/OTC
# החלף את הלינק ללינק של מסך סורק OTC שתיצור ב-TradingView
OTC_SCREENER_URL = "https://www.tradingview.com/screener/qS1IqGDa/"

# רשימת טיקרים בסיסית לגיבוי / בדיקה (Micro-caps / OTC)
FALLBACK_TICKERS = ["TLSS", "ALPP", "ABML", "ILUS", "AABB", "HMBL", "TSNP"]

def run_otc_pipeline():
    print("🚀 Starting OTC Market Scan (MVP Milestone 1)...")

    ai_service = AIService()
    target_tickers = set()

    # 1. איסוף המניות הפוטנציאליות
    print("🌍 Fetching OTC candidates from TradingView...")
    # אם הלינק לא מוגדר, נשתמש ברשימת הגיבוי לבדיקה
    if "YOUR_OTC_LINK_HERE" not in OTC_SCREENER_URL:
        tv_tickers = TradingViewService.get_candidates_from_url(OTC_SCREENER_URL)
        if tv_tickers:
            target_tickers.update(tv_tickers)
    else:
        print("⚠️ No TradingView URL provided. Using fallback OTC list.")
        target_tickers.update(FALLBACK_TICKERS)

    final_tickers = list(target_tickers)

    # XGBoost pre-filter: rank candidates by confidence (highest first)
    from app.services.xgb_filter import enrich_with_confidence, get_xgb_label, log_scan_candidates as _log_candidates
    _ranked = enrich_with_confidence(final_tickers)
    _conf_map = {t: c for c, t in _ranked}
    final_tickers = [t for _, t in _ranked]          # reordered by XGB confidence
    _log_candidates(final_tickers, source="otc")
    print(f"🤖 XGBoost ranked {len(final_tickers)} OTC candidates.")

    otc_opportunities = []

    print(f"🔎 Analyzing {len(final_tickers)} OTC stocks for Hard Rules (Price & RVOL)...")

    for ticker in final_tickers:
        # בדיקת הצפה - האם נשלח לאחרונה?
        if MongoDB.was_sent_recently(ticker, days=2):
            print(f"   ⏭️ Skipping {ticker} (Sent recently).")
            continue

        # 2. סינון לפי Hard Rules
        otc_data = OTCScanner.evaluate_hard_rules(ticker)

        if otc_data:
            print(f"   ✅ BOOM! {ticker} passed: RVOL {otc_data['rvol']}x, Price ${otc_data['price']}")

            # 3. הפעלת ה-AI להסבר העלייה
            prompt_headline = f"OTC Stock Alert: RVOL is {otc_data['rvol']}x average. Price changed by {otc_data['pct_change']}%. Why might this penny stock be surging today? Check for press releases, sector momentum, or short squeezes."

            # מעבירים ל-AI נתונים בסיסיים כדי שיעזור בניתוח
            fake_fin_data = {
                "current_price": otc_data['price'],
                "volume": otc_data['volume']
            }

            ai_result = ai_service.analyze_stock(ticker, prompt_headline, fake_fin_data)

            xgb_conf = _conf_map.get(ticker, 0.0)
            otc_opportunities.append({
                "ticker": ticker,
                "headline": f"🔥 OTC Alert: {otc_data['rvol']}x Volume Surge!",
                "score": 85, # ציון גבוה כדי שיבלוט
                "price": otc_data['price'],
                "financials": fake_fin_data,
                "ai_hebrew_desc": ai_result['hebrew_desc'],
                "ai_analysis": ai_result['analysis'],
                "xgb_confidence": xgb_conf,
                "xgb_label": get_xgb_label(xgb_conf),
            })

            # שמירה ב-DB לאימון מודל ה-Machine Learning העתידי (מייסטון 2)
            MongoDB.log_sent_alert(ticker, f"OTC RVOL {otc_data['rvol']}")

        time.sleep(1) # השהייה קלה למניעת חסימה מ-Yahoo

    # 4. שליחת המייל
    if otc_opportunities:
        otc_opportunities.sort(key=lambda x: x['score'], reverse=True)
        # נשתמש בשירות המייל הקיים, אפשר להעביר רשימה ריקה לחדשות הכלליות
        EmailService.send_report(otc_opportunities, [])
        print("📨 OTC Alert Email sent successfully!")
    else:
        print("💤 No OTC stocks passed the Hard Rules today.")

if __name__ == "__main__":
    run_otc_pipeline()