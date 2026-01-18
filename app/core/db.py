from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# 1. יצירת המנוע - מותאם ל-Postgres של Render
# pool_pre_ping עוזר למנוע שגיאות ניתוק (Server closed connection)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# 2. הגדרת ה-Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. מחלקת הבסיס למודלים
class Base(DeclarativeBase):
    pass

# 4. פונקציה ליצירת הטבלאות (נקראת בתחילת הסריקה)
def init_db():
    try:
        # ייבוא המודלים בתוך הפונקציה כדי למנוע Circular Import
        from app.models.models import AlertHistory

        print("🛠️ Creating tables in database if they don't exist...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

# 5. Dependency לשימוש ב-API (אם תרצה בעתיד)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()