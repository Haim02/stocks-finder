import logging
from datetime import datetime, timedelta

import certifi
import pytz
from pymongo import MongoClient
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    _client = None

    @classmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_db(cls):
        if cls._client is None:
            import os
            # Log which variable supplied the URI so Railway deployments are easy to debug
            source = (
                "MONGODB_URL (Railway)"  if os.getenv("MONGODB_URL")
                else "MONGO_URI (.env)"  if os.getenv("MONGO_URI")
                else "hardcoded fallback"
            )
            logger.info("Connecting to MongoDB via %s ...", source)
            cls._client = MongoClient(
                settings.MONGO_URI,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=10_000,
                connectTimeoutMS=10_000,
                maxPoolSize=10,
            )
        return cls._client[settings.DB_NAME]

    @classmethod
    def save_news_event(cls, ticker: str, news_item: dict):
        """Saves a news item (upsert by URL to prevent duplicates)."""
        try:
            db = cls.get_db()
            raw_date = news_item.get("published_at") or news_item.get("raw_date")
            if isinstance(raw_date, str):
                try:
                    dt_object = datetime.fromisoformat(raw_date)
                except ValueError:
                    dt_object = datetime.now(pytz.utc)
            else:
                dt_object = raw_date or datetime.now(pytz.utc)

            db.news_events.update_one(
                {"url": news_item["url"]},
                {
                    "$setOnInsert": {
                        "ticker": ticker,
                        "headline": news_item["headline"],
                        "news_date": dt_object,
                        "processed_for_training": False,
                        "created_at": datetime.now(pytz.utc),
                    }
                },
                upsert=True,
            )
        except Exception:
            logger.exception("Failed to save news event for %s", ticker)

    @classmethod
    def get_unlabeled_data(cls) -> list:
        """Returns news events not yet used for training."""
        try:
            db = cls.get_db()
            return list(db.news_events.find({"processed_for_training": False}))
        except Exception:
            logger.exception("Failed to fetch unlabeled data")
            return []

    @classmethod
    def mark_as_processed(cls, doc_id):
        """Marks a news event as used for training."""
        try:
            db = cls.get_db()
            db.news_events.update_one(
                {"_id": doc_id}, {"$set": {"processed_for_training": True}}
            )
        except Exception:
            logger.exception("Failed to mark doc %s as processed", doc_id)

    # --- Spam Filter (Cooldown) ---

    @classmethod
    def log_sent_alert(cls, ticker: str, reason: str):
        """Records that a ticker was included in an email alert."""
        try:
            db = cls.get_db()
            db.sent_alerts.insert_one(
                {
                    "ticker": ticker,
                    "reason": reason,
                    "sent_at": datetime.now(pytz.utc),
                }
            )
        except Exception:
            logger.exception("Failed to log sent alert for %s", ticker)

    @classmethod
    def was_sent_recently(cls, ticker: str, days: int = 3) -> bool:
        """Returns True if this ticker was alerted within the last `days` days."""
        try:
            db = cls.get_db()
            cutoff = datetime.now(pytz.utc) - timedelta(days=days)
            return (
                db.sent_alerts.count_documents(
                    {"ticker": ticker, "sent_at": {"$gte": cutoff}}
                )
                > 0
            )
        except Exception:
            logger.exception("Failed to check sent_recently for %s", ticker)
            return False

    # --- Scanner Candidates (for market intelligence pipeline) ---

    @classmethod
    def save_scanner_candidates(cls, tickers: list[str], source: str) -> None:
        """
        Records every ticker surfaced by a screener run (Finviz / TradingView /
        Smart Money).  One document per (ticker, source) — the timestamp is
        refreshed on every call so get_recent_scanner_candidates() always sees
        the freshest scan time.

        Collection: scanner_candidates
        """
        if not tickers:
            return
        try:
            db  = cls.get_db()
            now = datetime.now(pytz.utc)
            for ticker in tickers:
                db.scanner_candidates.update_one(
                    {"ticker": ticker.upper(), "source": source},
                    {"$set": {"ticker": ticker.upper(), "source": source,
                              "scanned_at": now}},
                    upsert=True,
                )
            logger.info(
                "Saved %d scanner candidates from source '%s'.", len(tickers), source
            )
        except Exception:
            logger.exception("Failed to save scanner candidates (source=%s)", source)

    @classmethod
    def save_scanner_candidate(cls, ticker: str, source: str) -> None:
        """Upsert a single scanner candidate (convenience wrapper)."""
        cls.save_scanner_candidates([ticker], source)

    @classmethod
    def get_recent_scanner_candidates(cls, hours: int = 48) -> list[str]:
        """
        Returns deduplicated tickers that appeared in any screener run within
        the last `hours` hours, sorted alphabetically.
        """
        try:
            db     = cls.get_db()
            cutoff = datetime.now(pytz.utc) - timedelta(hours=hours)
            docs   = db.scanner_candidates.find(
                {"scanned_at": {"$gte": cutoff}},
                {"ticker": 1, "_id": 0},
            )
            return sorted({d["ticker"] for d in docs})
        except Exception:
            logger.exception("Failed to fetch recent scanner candidates")
            return []

    # --- Market Intelligence / Daily Sentiment ---

    @classmethod
    def save_daily_sentiment(cls, doc: dict):
        """
        Upserts one sentiment record per (ticker, date).
        Collection: daily_market_sentiment
        """
        try:
            db = cls.get_db()
            db.daily_market_sentiment.update_one(
                {"ticker": doc["ticker"], "date": doc["date"]},
                {"$set": doc},
                upsert=True,
            )
        except Exception:
            logger.exception(
                "Failed to save daily sentiment for %s", doc.get("ticker")
            )

    @classmethod
    def get_sentiment_history(cls, ticker: str, days: int = 730) -> list[dict]:
        """
        Returns sentiment records for the last `days` days for a ticker,
        sorted ascending by date. Fields: date, sentiment_score,
        key_event_type, impact_duration.
        """
        try:
            from datetime import date as _date, timedelta
            cutoff = (_date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
            db = cls.get_db()
            return list(
                db.daily_market_sentiment.find(
                    {"ticker": ticker.upper(), "date": {"$gte": cutoff}},
                    {
                        "_id": 0,
                        "date": 1,
                        "sentiment_score": 1,
                        "key_event_type": 1,
                        "impact_duration": 1,
                    },
                ).sort("date", 1)
            )
        except Exception:
            logger.exception(
                "Failed to fetch sentiment history for %s", ticker
            )
            return []

    # --- Options Cooldown ---

    @classmethod
    def log_options_sent(cls, ticker: str) -> None:
        """Records that a ticker was included in an options email."""
        try:
            db = cls.get_db()
            db.sent_options.insert_one({
                "ticker": ticker.upper(),
                "sent_at": datetime.now(pytz.utc),
            })
        except Exception:
            logger.exception("Failed to log options sent for %s", ticker)

    @classmethod
    def was_options_sent_recently(cls, ticker: str, days: int = 4) -> bool:
        """Returns True if this ticker appeared in an options email within the last `days` days."""
        try:
            db = cls.get_db()
            cutoff = datetime.now(pytz.utc) - timedelta(days=days)
            return (
                db.sent_options.count_documents(
                    {"ticker": ticker.upper(), "sent_at": {"$gte": cutoff}}
                )
                > 0
            )
        except Exception:
            logger.exception("Failed to check options cooldown for %s", ticker)
            return False

    # --- Strategy Cooldown ---

    @classmethod
    def log_strategy_sent(cls, ticker: str, strategy_name: str, price: float) -> None:
        """Records that a strategy was recommended for a ticker via /strategies."""
        try:
            db = cls.get_db()
            db.sent_strategies.insert_one({
                "ticker":        ticker.upper(),
                "strategy_name": strategy_name,
                "price":         price,
                "sent_at":       datetime.now(pytz.utc),
            })
        except Exception:
            logger.exception("Failed to log strategy sent for %s", ticker)

    @classmethod
    def was_strategy_sent_recently(cls, ticker: str, days: int = 5) -> bool:
        """Returns True if a strategy was sent for this ticker within the last `days` days."""
        try:
            db = cls.get_db()
            cutoff = datetime.now(pytz.utc) - timedelta(days=days)
            return (
                db.sent_strategies.count_documents(
                    {"ticker": ticker.upper(), "sent_at": {"$gte": cutoff}}
                )
                > 0
            )
        except Exception:
            logger.exception("Failed to check strategy cooldown for %s", ticker)
            return False

    @classmethod
    def ensure_indexes(cls) -> None:
        """Create TTL and unique indexes — idempotent, safe to call on every startup."""
        try:
            from pymongo import ASCENDING, DESCENDING
            db = cls.get_db()

            # news_alerts_log — TTL 7 days + query index
            db["news_alerts_log"].create_index(
                [("timestamp", ASCENDING)],
                expireAfterSeconds=7 * 24 * 3600,
                name="ttl_7d",
                background=True,
            )
            db["news_alerts_log"].create_index(
                [("ticker", ASCENDING), ("timestamp", DESCENDING)],
                name="ticker_ts",
                background=True,
            )

            # user_settings — unique key index
            db["user_settings"].create_index(
                [("key", ASCENDING)],
                unique=True,
                name="unique_key",
                background=True,
            )

            logger.info("MongoDB indexes ensured (news_alerts_log TTL + user_settings unique)")
        except Exception as e:
            logger.warning("ensure_indexes failed (non-fatal): %s", e)

    @classmethod
    def save_institutional_pick(cls, pick_data: dict):
        """Saves a stock that passed the Smart Money filter (upsert per day)."""
        try:
            db = cls.get_db()
            pick_id = f"{pick_data['ticker']}_{datetime.now(pytz.utc).strftime('%Y-%m-%d')}"
            document = {
                "ticker": pick_data["ticker"],
                "score": pick_data["score"],
                "reasons": pick_data["reasons"],
                "fundamental_strength": pick_data["fundamentals"],
                "technical_setup": pick_data["technicals"],
                "dark_pool_link": f"https://stockgrid.io/darkpools/{pick_data['ticker']}",
                "created_at": datetime.now(pytz.utc),
            }
            db.institutional_picks.update_one(
                {"_id": pick_id}, {"$set": document}, upsert=True
            )
        except Exception:
            logger.exception(
                "Failed to save institutional pick for %s", pick_data.get("ticker")
            )
