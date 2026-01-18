from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.core.db import Base

class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    price = Column(Float)
    signal_type = Column(String)
    reasons = Column(String, nullable=True)  # הוספנו את העמודה הזו!
    timestamp = Column(DateTime(timezone=True), server_default=func.now())