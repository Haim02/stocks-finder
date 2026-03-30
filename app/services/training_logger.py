"""
Training data logger — records every ticker surfaced by scan pipelines so that
after 10 trading days we can label it (did price rise ≥5%?) and retrain XGBoost.

Collection: training_events
Schema:
  ticker          str
  source          str   — "daily_scan" | "options_scan" | "news_scan" | ...
  scan_at         datetime (UTC)
  price_at_scan   float
  xgb_conf        float | None
  strategy_name   str | None
  ai_score        int | None
  labeled         bool  (default False)
  label           bool | None   — True if price rose ≥5% after 10 days
  labeled_at      datetime | None
"""
import logging
from datetime import datetime, timedelta

import pytz

logger = logging.getLogger(__name__)


def log_training_event(
    ticker: str,
    source: str,
    price: float,
    xgb_conf: float | None = None,
    strategy_name: str | None = None,
    ai_score: int | None = None,
) -> None:
    """
    Upsert one training event per (ticker, source, date).
    Safe to call multiple times — only the first call for the day is stored.
    """
    try:
        from app.data.mongo_client import MongoDB
        db  = MongoDB.get_db()
        now = datetime.now(pytz.utc)
        day = now.strftime("%Y-%m-%d")
        db.training_events.update_one(
            {"ticker": ticker.upper(), "source": source, "scan_day": day},
            {
                "$setOnInsert": {
                    "ticker":        ticker.upper(),
                    "source":        source,
                    "scan_day":      day,
                    "scan_at":       now,
                    "price_at_scan": price,
                    "xgb_conf":      xgb_conf,
                    "strategy_name": strategy_name,
                    "ai_score":      ai_score,
                    "labeled":       False,
                    "label":         None,
                    "labeled_at":    None,
                }
            },
            upsert=True,
        )
        logger.debug("training_event logged: %s source=%s price=%.2f", ticker, source, price)
    except Exception:
        logger.warning("Failed to log training event for %s", ticker, exc_info=True)


def get_unlabeled_events(lookback_days: int = 20) -> list[dict]:
    """
    Returns training events older than 10 days and not yet labeled,
    so the /train command can fetch closing prices and assign labels.
    """
    try:
        from app.data.mongo_client import MongoDB
        db     = MongoDB.get_db()
        cutoff = datetime.now(pytz.utc) - timedelta(days=10)
        docs   = list(db.training_events.find(
            {
                "labeled": False,
                "scan_at": {"$lte": cutoff},
            },
            {"_id": 1, "ticker": 1, "source": 1, "price_at_scan": 1, "scan_at": 1},
        ).sort("scan_at", 1).limit(500))
        return docs
    except Exception:
        logger.warning("Failed to fetch unlabeled training events", exc_info=True)
        return []


def mark_event_labeled(doc_id, label: bool) -> None:
    """Mark a training event as labeled with the outcome."""
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        db.training_events.update_one(
            {"_id": doc_id},
            {"$set": {"labeled": True, "label": label, "labeled_at": datetime.now(pytz.utc)}},
        )
    except Exception:
        logger.warning("Failed to mark training event labeled: %s", doc_id, exc_info=True)
