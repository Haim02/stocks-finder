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



# import pandas as pd
# import yfinance as yf
# from datetime import datetime, timedelta
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.ensemble import RandomForestClassifier
# import joblib
# import os
# import pytz
# from app.data.mongo_client import MongoDB

# # הגדרות לאימון
# MODEL_PATH = "app/models/news_classifier.pkl"
# VECTORIZER_PATH = "app/models/tfidf_vectorizer.pkl"
# MIN_SAMPLES_TO_TRAIN = 10

# def get_price_change(ticker, date):
#     """
#     בודק האם המחיר עלה ב-3 הימים שלאחר החדשות.
#     """
#     try:
#         if date.tzinfo is None:
#             date = date.replace(tzinfo=pytz.utc)

#         start_date = date
#         end_date = date + timedelta(days=4)

#         stock = yf.Ticker(ticker)
#         df = stock.history(start=start_date.strftime('%Y-%m-%d'),
#                            end=end_date.strftime('%Y-%m-%d'))

#         if df.empty or len(df) < 2:
#             return None

#         open_price = df['Open'].iloc[0]
#         close_price = df['Close'].iloc[-1]
#         max_price = df['High'].max()

#         change_close = (close_price - open_price) / open_price
#         change_high = (max_price - open_price) / open_price

#         # תנאי הצלחה: עלייה של 3% בסגירה או זינוק של 5% במהלך היום
#         if change_close > 0.03 or change_high > 0.05:
#             return 1
#         return 0

#     except Exception as e:
#         return None

# def train_model():
#     print("🧠 Starting Training Process (Duplicates Filter Enabled)...")

#     raw_data = MongoDB.get_unlabeled_data()

#     if not raw_data:
#         print("📭 Database is empty or all items processed.")
#         return

#     print(f"📥 Found {len(raw_data)} items. Filtering duplicates & mature data...")

#     labeled_news = []
#     labels = []

#     # --- התיקון: זיכרון לכותרות שראינו כבר ---
#     seen_headlines = set()

#     processed_count = 0
#     skipped_count = 0
#     duplicates_count = 0 # מונה כפילויות

#     now = datetime.now(pytz.utc)

#     for item in raw_data:
#         ticker = item.get('ticker')
#         headline = item.get('headline')

#         # 1. סינון כפילויות מיידי
#         if headline in seen_headlines:
#             # מסמנים כטופל כדי שלא יופיע בפעם הבאה, אבל לא לומדים מזה שוב
#             MongoDB.mark_as_processed(item['_id'])
#             duplicates_count += 1
#             continue

#         # הוספה לזיכרון
#         seen_headlines.add(headline)

#         # המרת תאריך
#         news_date = item.get('news_date')
#         if isinstance(news_date, str):
#             try:
#                 news_date = datetime.fromisoformat(news_date)
#             except:
#                 MongoDB.mark_as_processed(item['_id'])
#                 continue

#         if news_date.tzinfo is None:
#             news_date = news_date.replace(tzinfo=pytz.utc)

#         # 2. האם עברו 3 ימים?
#         if (now - news_date).days < 3:
#             skipped_count += 1
#             continue

#         if not ticker or ticker == "GENERAL":
#             MongoDB.mark_as_processed(item['_id'])
#             continue

#         # 3. בדיקת מחיר
#         label = get_price_change(ticker, news_date)

#         if label is not None:
#             labeled_news.append(headline)
#             labels.append(label)
#             print(f"   ✅ Learned: {ticker} -> {label}") # ידפיס כל כותרת רק פעם אחת
#             processed_count += 1
#         else:
#             print(f"   ⚠️ No data for {ticker}, skipping.")

#         # סימון ב-DB
#         MongoDB.mark_as_processed(item['_id'])

#     print(f"\n📊 Summary:")
#     print(f"   - Original items: {len(raw_data)}")
#     print(f"   - Duplicates Removed: {duplicates_count}")
#     print(f"   - Too new (Skipped): {skipped_count}")
#     print(f"   - Successfully Trained: {processed_count}")

#     if len(labeled_news) < MIN_SAMPLES_TO_TRAIN:
#         print(f"⏳ Not enough unique data yet ({len(labeled_news)}/{MIN_SAMPLES_TO_TRAIN}).")
#         return

#     print(f"🎓 Training model on {len(labeled_news)} unique samples...")

#     vectorizer = TfidfVectorizer(stop_words='english', max_features=2000)
#     X = vectorizer.fit_transform(labeled_news)
#     y = labels

#     model = RandomForestClassifier(n_estimators=100, random_state=42)
#     model.fit(X, y)

#     if not os.path.exists("app/models"):
#         os.makedirs("app/models")

#     joblib.dump(model, MODEL_PATH)
#     joblib.dump(vectorizer, VECTORIZER_PATH)

#     print("🚀 Model successfully updated without duplicates!")

# if __name__ == "__main__":
#     train_model()


"""
XGBoost Price Model Trainer
============================
Fetches 2 years of OHLCV history for a broad universe of tickers (+ any tickers
stored in MongoDB), engineers technical + sentiment features, and trains an XGBoost
binary classifier to predict whether a stock will gain ≥5 % within the next 10
trading days.

Feature set:
  Technical  — RSI, SMA ratios, volume ratio, momentum (5/10/20d), ATR, BB width
  Sentiment  — LLM-scored daily sentiment (sent_score 1-10, sent_has_data flag)
               sourced from MongoDB daily_market_sentiment collection.
               Rows without a sentiment record default to neutral (5.0 / 0).

Usage:
    # 1. Populate sentiment data first (run daily):
    python run_market_intelligence.py

    # 2. Train (or retrain) the model:
    python train_model.py

Output:
    app/models/xgb_price_model.pkl
"""

import logging
import os
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import yfinance as yf

try:
    import xgboost as xgb
except ImportError:
    print("XGBoost is not installed. Run: pip install xgboost")
    raise

from app.services.ml_service import (
    FEATURE_COLS,
    FORWARD_DAYS,
    GAIN_THRESHOLD,
    XGB_MODEL_PATH,
    add_sentiment_features,
    extract_features,
    label_rows,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_DIR = os.path.dirname(XGB_MODEL_PATH)
MIN_ROWS_PER_TICKER = 60

# Broad training universe — S&P 500 sample + small/mid caps for variety
TRAINING_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
    "INTC", "CRM", "ADBE", "ORCL", "NFLX", "PYPL", "SQ", "SHOP",
    "SNAP", "TWLO", "ZM", "DDOG", "NET", "CRWD", "OKTA", "MDB",
    "PLTR", "RBLX", "COIN", "HOOD", "SOFI", "UPST", "AFRM",
    "JPM", "BAC", "GS", "MS", "C", "WFC", "AXP", "V", "MA",
    "XOM", "CVX", "OXY", "SLB", "HAL", "COP", "EOG",
    "PFE", "JNJ", "ABBV", "MRK", "LLY", "AMGN", "BIIB", "GILD", "REGN",
    "DIS", "PARA", "WBD",
    "TEVA", "RKT", "BABA", "BIDU", "NIO", "XPEV",
    "SPY", "QQQ", "IWM",
]


def get_training_tickers() -> list[str]:
    """Combine MongoDB picks with the default training universe."""
    tickers = set(TRAINING_UNIVERSE)
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        for doc in db["institutional_picks"].find({}, {"ticker": 1}):
            if t := doc.get("ticker"):
                tickers.add(t.upper())
        for doc in db["news_events"].find({}, {"ticker": 1}):
            if t := doc.get("ticker"):
                tickers.add(t.upper())
        logger.info("Total unique tickers (after MongoDB): %d", len(tickers))
    except Exception as exc:
        logger.warning("MongoDB ticker fetch failed (%s); using default universe.", exc)
    return sorted(tickers)


def build_dataset(tickers: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    """Download 2 years of OHLCV data and build (X, y) for training."""
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=730)
    all_X: list[pd.DataFrame] = []
    all_y: list[pd.Series]    = []

    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
            )
            if df.empty or len(df) < MIN_ROWS_PER_TICKER:
                logger.debug("Skipping %s — only %d rows", ticker, len(df))
                continue

            df           = extract_features(df)
            df           = add_sentiment_features(df, ticker)
            df["label"]  = label_rows(df)
            valid_mask   = df[FEATURE_COLS + ["label"]].notna().all(axis=1)
            df           = df[valid_mask]
            if len(df) < 30:
                continue

            all_X.append(df[FEATURE_COLS])
            all_y.append(df["label"])
            logger.info("  %-6s  %d rows", ticker, len(df))
        except Exception:
            logger.warning("Failed to process %s", ticker, exc_info=True)

    if not all_X:
        raise ValueError("No training data collected. Check tickers and network.")

    return pd.concat(all_X, ignore_index=True), pd.concat(all_y, ignore_index=True)


def train_xgb_model() -> None:
    """Train and save XGBoost model predicting ≥5 % gain in 10 trading days."""
    logger.info("=== XGBoost Price Model Training ===")
    logger.info(
        "Target: %.0f%% gain within %d trading days",
        GAIN_THRESHOLD * 100,
        FORWARD_DAYS,
    )

    tickers = get_training_tickers()
    logger.info("Training universe: %d tickers", len(tickers))

    X, y = build_dataset(tickers)

    pos_count = int((y == 1).sum())
    neg_count = int((y == 0).sum())
    pos_rate  = pos_count / len(y) * 100
    spw       = neg_count / pos_count if pos_count > 0 else 1.0
    logger.info(
        "Dataset: %d samples | Positive: %.1f%% | scale_pos_weight: %.2f",
        len(y), pos_rate, spw,
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=spw,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)
    logger.info("Training complete.")

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLS}, XGB_MODEL_PATH)
    logger.info("Model saved → %s", XGB_MODEL_PATH)

    sample = X.sample(min(10, len(X)), random_state=1)
    probs  = model.predict_proba(sample)[:, 1]
    logger.info("Sample confidence scores: %s", np.round(probs, 3))


if __name__ == "__main__":
    train_xgb_model()