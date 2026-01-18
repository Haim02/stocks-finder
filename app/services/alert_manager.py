from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models.models import AlertHistory
from app.core.config import settings

class AlertManager:
    def __init__(self, db: Session):
        self.db = db

    def is_in_cooldown(self, ticker: str) -> bool:
        """
        בודק אם המניה נשלחה ב-30 הימים האחרונים (או מה שמוגדר ב-Config)
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=settings.EMAIL_COOLDOWN_HOURS)

        # שאילתה: האם קיים רישום למניה הזו אחרי זמן החיתוך?
        stmt = select(AlertHistory).where(
            AlertHistory.ticker == ticker,
            AlertHistory.timestamp >= cutoff_time
        )
        result = self.db.execute(stmt).first()

        if result:
            print(f"🚫 {ticker} is in cooldown (sent in last {settings.EMAIL_COOLDOWN_HOURS} hours).")
            return True
        return False

    def record_alert(self, ticker: str, signal_type: str, price: float):
        """
        שומר את המניה בבסיס הנתונים כדי שלא תישלח שוב בקרוב
        """
        new_alert = AlertHistory(
            ticker=ticker,
            signal_type=signal_type,
            price=price,
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(new_alert)
        self.db.commit()
        print(f"✅ Recorded alert for {ticker} in DB.")

    def cleanup_old_alerts(self):
        """
        מוחק מניות ישנות מאוד (מעל חודש) כדי לא לסתום את ה-DB
        אופציונלי - ירוץ פעם ביום
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=settings.EMAIL_COOLDOWN_HOURS)
        stmt = delete(AlertHistory).where(AlertHistory.timestamp < cutoff_time)
        self.db.execute(stmt)
        self.db.commit()