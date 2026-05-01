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

    # 3-7. TTL indexes — auto-cleanup old documents
    ttl_indexes = [
        ("daily_market_sentiment",     "timestamp",  30 * 24 * 3600),
        ("market_regime_reports",      "timestamp",  30 * 24 * 3600),
        ("options_strategist_reports", "timestamp",  14 * 24 * 3600),
        ("agent_run_log",              "started_at",  7 * 24 * 3600),
        ("training_events",            "timestamp",  90 * 24 * 3600),
        ("monitor_alerts_log",         "timestamp",   7 * 24 * 3600),
    ]
    for collection, field, ttl in ttl_indexes:
        try:
            db[collection].create_index(field, expireAfterSeconds=ttl)
            print(f"✅ TTL index '{field}' on '{collection}' ({ttl // 86400}d).")
        except Exception as e:
            print(f"⚠️ TTL index '{collection}.{field}' info: {e}")

    print("🚀 MongoDB setup complete!")

if __name__ == "__main__":
    init_db()