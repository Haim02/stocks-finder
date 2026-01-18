from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API & Security
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY")
    # OPENAI_API_KEY: str
    # FINNHUB_API_KEY: str
    RESEND_API_KEY: str
    DATABASE_URL: str
    WEBHOOK_SECRET: str = "optional_secret"

    # Email Settings
    ALERT_TO_EMAIL: str
    FROM_EMAIL: str = "alerts@stocks-alerts.site"
    EMAIL_COOLDOWN_HOURS: int = 720

    # Strategy Settings (Price Action & Indicators)
    EMA_8: int = 8
    EMA_21: int = 21
    SMA_50: int = 50
    SMA_200: int = 200
    RSI_PERIOD: int = 14

    # Risk Management
    ACCOUNT_SIZE: float = 10000.0
    RISK_PCT: float = 0.01
    RR_MIN: float = 2.0

    # Render & Environment
    PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()