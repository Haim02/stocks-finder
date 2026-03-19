from app.data.mongo_client import MongoDB
from bson import ObjectId
import pytz

def heal_database():
    print("🚑 Starting Database Repair Operation...")
    db = MongoDB.get_db()
    collection = db.news_events

    # שליפת כל הרשומות (גם אלו שטופלו וגם אלו שלא)
    all_docs = collection.find({})

    fixed_count = 0
    skipped_count = 0

    for doc in all_docs:
        try:
            # בדיקה האם התאריך חסר או לא תקין
            current_date = doc.get('news_date')

            needs_fix = False

            if current_date is None:
                needs_fix = True
            elif isinstance(current_date, str):
                # אם זה מחרוזת ולא תאריך אמיתי - צריך לתקן
                needs_fix = True

            if needs_fix:
                # --- הקסם: חילוץ התאריך מתוך ה-ID ---
                # ה-ObjectId מכיל את זמן היצירה של המסמך
                creation_time = doc['_id'].generation_time

                # המרה ל-UTC כדי למנוע בעיות אזור זמן
                fixed_date = creation_time.replace(tzinfo=pytz.utc)

                # עדכון המסמך ב-DB
                collection.update_one(
                    {'_id': doc['_id']},
                    {
                        '$set': {
                            'news_date': fixed_date,
                            'processed_for_training': False # מחזירים ל-False כדי שהמודל ינסה ללמוד מזה שוב!
                        }
                    }
                )
                fixed_count += 1
                print(f"   🔧 Fixed: {doc.get('headline', 'Unknown')} -> {fixed_date}")
            else:
                skipped_count += 1

        except Exception as e:
            print(f"Error fixing doc {doc.get('_id')}: {e}")

    print("-" * 50)
    print(f"✅ Repair Complete!")
    print(f"   - Fixed & Restored: {fixed_count} records")
    print(f"   - Already Good: {skipped_count} records")
    print("\nעכשיו אתה יכול להריץ את train_model.py שוב!")

if __name__ == "__main__":
    heal_database()