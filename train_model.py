# import pandas as pd
# import yfinance as yf
# from datetime import timedelta
# from app.data.mongo_client import MongoDB
# from app.services.news_model import NewsModel

# def get_price_change(ticker, date_obj):
#     """בודק אם המניה עלתה ביומיים שאחרי התאריך"""
#     try:
#         start = date_obj
#         end = date_obj + timedelta(days=5)
#         df = yf.download(ticker, start=start, end=end, progress=False)
#         if len(df) < 3: return None

#         close_prices = df['Close']
#         start_price = close_prices.iloc[0]
#         end_price = close_prices.iloc[2] # T+2

#         return (end_price - start_price) / start_price
#     except:
#         return None

# def main():
#     print("🎓 Starting Training Process...")
#     db_items = MongoDB.get_unlabeled_data()

#     training_data = []

#     for item in db_items:
#         # בדיקת מה קרה במציאות
#         change = get_price_change(item['ticker'], item['news_date'])

#         if change is not None:
#             # תיוג: 1 אם עלתה מעל 2%, אחרת 0
#             is_winner = 1 if change > 0.02 else 0

#             training_data.append({
#                 "headline": item['headline'],
#                 "is_winner": is_winner
#             })

#             # סימון ב-DB שהרשומה עובדה
#             # (כאן יש להוסיף קוד לעדכון המסמך ב-Mongo ל-processed=True)

#     if len(training_data) > 50:
#         df = pd.DataFrame(training_data)
#         model = NewsModel()
#         model.train(df)
#     else:
#         print(f"⚠️ Not enough data yet ({len(training_data)} samples). Need at least 50.")

# if __name__ == "__main__":
#     main()



# import pandas as pd
# import yfinance as yf
# from datetime import timedelta
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.ensemble import RandomForestClassifier
# import joblib
# import os
# from app.data.mongo_client import MongoDB

# # הגדרות לאימון
# MODEL_PATH = "app/models/news_classifier.pkl"
# VECTORIZER_PATH = "app/models/tfidf_vectorizer.pkl"
# MIN_SAMPLES_TO_TRAIN = 50  # לא מתחילים לאמן לפני שיש 50 דוגמאות

# def get_price_change(ticker, date):
#     """
#     בודק האם המחיר עלה ביומיים שלאחר החדשות.
#     מחזיר 1 אם עלה מעל 2% (חדשה טובה), אחרת 0.
#     """
#     try:
#         # בדיקת מחיר בטווח של 3 ימים מהחדשה
#         start_date = date
#         end_date = date + timedelta(days=3)

#         stock = yf.Ticker(ticker)
#         df = stock.history(start=start_date, end=end_date)

#         if len(df) < 2:
#             return None # אין מספיק נתונים (אולי סופ"ש)

#         open_price = df['Open'].iloc[0]
#         close_price = df['Close'].iloc[-1]

#         # חישוב אחוז שינוי
#         pct_change = (close_price - open_price) / open_price

#         # התיוג: אם המניה עלתה יותר מ-2%, נחשיב את זה כחדשה חיובית (1)
#         if pct_change > 0.02:
#             return 1
#         return 0

#     except Exception as e:
#         print(f"⚠️ Error checking price for {ticker}: {e}")
#         return None

# def train_model():
#     print("🧠 Starting Model Training process...")

#     # 1. שליפת חדשות חדשות מה-DB
#     raw_data = MongoDB.get_unlabeled_data()

#     if not raw_data:
#         print("📭 No new data to process.")
#         return

#     print(f"📥 Processing {len(raw_data)} new news items...")

#     labeled_news = []
#     labels = []

#     for item in raw_data:
#         ticker = item.get('ticker')

#         # --- השינוי החשוב: סינון חדשות כלליות ---
#         # אם אין טיקר או שזה GENERAL, אי אפשר לבדוק מחיר מניה
#         if not ticker or ticker == "GENERAL":
#             # נסמן כמעובד כדי שלא יופיע שוב, אבל לא נלמד מזה
#             MongoDB.mark_as_processed(item['_id'])
#             continue

#         # בדיקת "התשובה הנכונה" (האם המחיר עלה?)
#         label = get_price_change(ticker, item['news_date'])

#         if label is not None:
#             labeled_news.append(item['headline'])
#             labels.append(label)
#             print(f"   ✅ Labeled: {ticker} -> {label}")

#         # סימון ב-DB שהחדשה הזו טופלה
#         MongoDB.mark_as_processed(item['_id'])

#     # אם אין מספיק דוגמאות חדשות לאימון
#     if len(labeled_news) < 10:
#         print("⏳ Not enough labeled data yet to update model. Waiting for more.")
#         return

#     # 2. טעינת נתונים ישנים (אם יש) ושילוב עם החדשים
#     # (בגרסה מתקדמת נשמור דאטה-סט בקובץ CSV נפרד, כרגע נאמן מחדש על מה שיש)

#     # בדיקה האם יש לנו מספיק דאטה כולל בסך הכל
#     if len(labeled_news) < MIN_SAMPLES_TO_TRAIN:
#          print(f"⚠️ Collected {len(labeled_news)} samples total. Need {MIN_SAMPLES_TO_TRAIN} to start training.")
#          return

#     # 3. אימון המודל
#     print(f"🎓 Training model on {len(labeled_news)} samples...")

#     vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
#     X = vectorizer.fit_transform(labeled_news)
#     y = labels

#     model = RandomForestClassifier(n_estimators=100, random_state=42)
#     model.fit(X, y)

#     # 4. שמירת המודל
#     if not os.path.exists("app/models"):
#         os.makedirs("app/models")

#     joblib.dump(model, MODEL_PATH)
#     joblib.dump(vectorizer, VECTORIZER_PATH)

#     print("🚀 Model updated and saved successfully!")

# if __name__ == "__main__":
#     train_model()



import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import pytz
from app.data.mongo_client import MongoDB

# הגדרות לאימון
MODEL_PATH = "app/models/news_classifier.pkl"
VECTORIZER_PATH = "app/models/tfidf_vectorizer.pkl"
MIN_SAMPLES_TO_TRAIN = 10

def get_price_change(ticker, date):
    """
    בודק האם המחיר עלה ב-3 הימים שלאחר החדשות.
    """
    try:
        if date.tzinfo is None:
            date = date.replace(tzinfo=pytz.utc)

        start_date = date
        end_date = date + timedelta(days=4)

        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date.strftime('%Y-%m-%d'),
                           end=end_date.strftime('%Y-%m-%d'))

        if df.empty or len(df) < 2:
            return None

        open_price = df['Open'].iloc[0]
        close_price = df['Close'].iloc[-1]
        max_price = df['High'].max()

        change_close = (close_price - open_price) / open_price
        change_high = (max_price - open_price) / open_price

        # תנאי הצלחה: עלייה של 3% בסגירה או זינוק של 5% במהלך היום
        if change_close > 0.03 or change_high > 0.05:
            return 1
        return 0

    except Exception as e:
        return None

def train_model():
    print("🧠 Starting Training Process (Duplicates Filter Enabled)...")

    raw_data = MongoDB.get_unlabeled_data()

    if not raw_data:
        print("📭 Database is empty or all items processed.")
        return

    print(f"📥 Found {len(raw_data)} items. Filtering duplicates & mature data...")

    labeled_news = []
    labels = []

    # --- התיקון: זיכרון לכותרות שראינו כבר ---
    seen_headlines = set()

    processed_count = 0
    skipped_count = 0
    duplicates_count = 0 # מונה כפילויות

    now = datetime.now(pytz.utc)

    for item in raw_data:
        ticker = item.get('ticker')
        headline = item.get('headline')

        # 1. סינון כפילויות מיידי
        if headline in seen_headlines:
            # מסמנים כטופל כדי שלא יופיע בפעם הבאה, אבל לא לומדים מזה שוב
            MongoDB.mark_as_processed(item['_id'])
            duplicates_count += 1
            continue

        # הוספה לזיכרון
        seen_headlines.add(headline)

        # המרת תאריך
        news_date = item.get('news_date')
        if isinstance(news_date, str):
            try:
                news_date = datetime.fromisoformat(news_date)
            except:
                MongoDB.mark_as_processed(item['_id'])
                continue

        if news_date.tzinfo is None:
            news_date = news_date.replace(tzinfo=pytz.utc)

        # 2. האם עברו 3 ימים?
        if (now - news_date).days < 3:
            skipped_count += 1
            continue

        if not ticker or ticker == "GENERAL":
            MongoDB.mark_as_processed(item['_id'])
            continue

        # 3. בדיקת מחיר
        label = get_price_change(ticker, news_date)

        if label is not None:
            labeled_news.append(headline)
            labels.append(label)
            print(f"   ✅ Learned: {ticker} -> {label}") # ידפיס כל כותרת רק פעם אחת
            processed_count += 1
        else:
            print(f"   ⚠️ No data for {ticker}, skipping.")

        # סימון ב-DB
        MongoDB.mark_as_processed(item['_id'])

    print(f"\n📊 Summary:")
    print(f"   - Original items: {len(raw_data)}")
    print(f"   - Duplicates Removed: {duplicates_count}")
    print(f"   - Too new (Skipped): {skipped_count}")
    print(f"   - Successfully Trained: {processed_count}")

    if len(labeled_news) < MIN_SAMPLES_TO_TRAIN:
        print(f"⏳ Not enough unique data yet ({len(labeled_news)}/{MIN_SAMPLES_TO_TRAIN}).")
        return

    print(f"🎓 Training model on {len(labeled_news)} unique samples...")

    vectorizer = TfidfVectorizer(stop_words='english', max_features=2000)
    X = vectorizer.fit_transform(labeled_news)
    y = labels

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    if not os.path.exists("app/models"):
        os.makedirs("app/models")

    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)

    print("🚀 Model successfully updated without duplicates!")

if __name__ == "__main__":
    train_model()