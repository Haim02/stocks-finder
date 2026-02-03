from app.data.mongo_client import MongoDB
import pymongo

def init_db():
    print("🛠️ Setting up MongoDB indexes...")
    db = MongoDB.get_db()

    # 1. יצירת אינדקס ייחודי ל-URL (מונע כפילויות)
    # 1 מייצג ASCENDING (סדר עולה)
    try:
        db.news_events.create_index([("url", 1)], unique=True)
        print("✅ Index 'url' created (Unique).")
    except Exception as e:
        print(f"⚠️ Index 'url' info: {e}")

    # 2. יצירת אינדקס תאריך (לשליפות מהירות של 'הכי חדש')
    # -1 מייצג DESCENDING (סדר יורד)
    try:
        db.news_events.create_index([("news_date", -1)])
        print("✅ Index 'news_date' created (Descending).")
    except Exception as e:
        print(f"⚠️ Index 'news_date' info: {e}")

    print("🚀 MongoDB setup complete!")

if __name__ == "__main__":
    init_db()