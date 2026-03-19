from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # ── MongoDB ───────────────────────────────────────────────────────────────
    # Priority: Railway injects MONGODB_URL; local .env uses MONGO_URI.
    # Falls back to the Atlas URI if neither is set.
    MONGO_URI: str = (
        os.getenv("MONGODB_URL")         # Railway variable name (injected automatically)
        or os.getenv("MONGO_URI")        # local .env / other platforms
        or "mongodb://localhost:27017"   # local dev fallback (no credentials needed)
    )
    DB_NAME: str = "stocks_finder"

    # ── Email (SMTP / Resend) ─────────────────────────────────────────────────
    EMAIL_SENDER:   Optional[str] = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER: Optional[str] = os.getenv("EMAIL_RECEIVER")

    # ── Core API keys ─────────────────────────────────────────────────────────
    OPENAI_API_KEY:  Optional[str] = os.getenv("OPENAI_API_KEY")
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")
    RESEND_API_KEY:  Optional[str] = os.getenv("RESEND_API_KEY")
    WEBHOOK_SECRET:  str           = os.getenv("WEBHOOK_SECRET", "optional_secret")

    # DATABASE_URL is optional — only needed for Postgres features.
    # Railway injects it automatically when a Postgres plugin is attached.
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # ── Premium market data APIs (all optional — services degrade gracefully) ─
    MARKETSTACK_API_KEY:   Optional[str] = os.getenv("MARKETSTACK_API_KEY")
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    FINAGE_API_KEY:        Optional[str] = os.getenv("FINAGE_API_KEY")
    FRED_API_KEY:          Optional[str] = os.getenv("FRED_API_KEY")
    ALETHEIA_API_KEY:      Optional[str] = os.getenv("ALETHEIA_API_KEY")
    ALPACA_API_KEY:        Optional[str] = os.getenv("ALPACA_API_KEY")
    ALPACA_API_SECRET:     Optional[str] = os.getenv("ALPACA_API_SECRET")

    # ── Telegram Bot (optional — mobile access to the trading agent) ──────────
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID:   Optional[str] = os.getenv("TELEGRAM_CHAT_ID")

    # ── Email delivery settings ───────────────────────────────────────────────
    ALERT_TO_EMAIL:       Optional[str] = os.getenv("ALERT_TO_EMAIL")
    FROM_EMAIL:           str           = os.getenv("FROM_EMAIL", "alerts@stocks-alerts.site")
    EMAIL_COOLDOWN_HOURS: int           = 720

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