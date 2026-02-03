from app.data.mongo_client import MongoDB

def reset_training_flags():
    print("🔄 Resetting training flags in Database...")
    db = MongoDB.get_db()

    # משנה את הסטטוס של כל החדשות ל-"לא טופל" (False)
    result = db.news_events.update_many(
        {},
        {'$set': {'processed_for_training': False}}
    )

    print(f"✅ Reset complete! {result.modified_count} items are ready for re-training.")

if __name__ == "__main__":
    reset_training_flags()