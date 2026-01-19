import sys
import os

# הוספת נתיב העבודה כדי שהסקריפט יזהה את app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import Base, engine, init_db

def perform_reset():
    print("📢 Starting Database Reset...")
    try:
        # מחיקת כל הטבלאות הקיימות
        print("🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)

        # יצירה מחדש של המבנה
        print("🏗️  Recreating tables from models...")
        init_db()

        print("✅ Success! Database is now empty and ready.")
    except Exception as e:
        print(f"❌ Error during reset: {e}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete ALL data? (y/n): ")
    if confirm.lower() == 'y':
        perform_reset()
    else:
        print("❌ Reset cancelled.")