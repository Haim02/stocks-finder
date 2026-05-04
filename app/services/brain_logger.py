"""
brain_logger.py — Central Learning Brain
=========================================

Every interaction teaches the agent.
Everything gets logged for XGBoost training:

1. Free chat — what stocks were discussed, what happened after
2. News alerts — did the prediction come true?
3. Images — what chart patterns were seen
4. URLs/PDFs — what knowledge was extracted
5. Scans — which opportunities were found and if they worked
6. Options strategies — did the trade work?
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def log_interaction(
    interaction_type: str,   # "chat", "scan", "alert", "image", "url", "strategy"
    content: str,            # what was discussed/found
    tickers: list[str] = None,
    strategy: str = "",
    price_at_time: float = 0,
    metadata: dict = None,
):
    """Log any interaction to MongoDB for XGBoost training."""
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()

        doc = {
            "type": interaction_type,
            "content": content[:500],
            "tickers": tickers or [],
            "strategy": strategy,
            "price_at_time": price_at_time,
            "metadata": metadata or {},
            "timestamp": datetime.now(),
            "price_24h_later": None,
            "price_1w_later": None,
            "outcome": None,  # "correct", "incorrect", "neutral"
        }

        db["brain_training_data"].insert_one(doc)

    except Exception as e:
        logger.debug("Brain log failed: %s", e)


def update_all_outcomes():
    """
    Update price outcomes for all logged interactions.
    Called during /train — fills in what happened after each interaction.
    """
    import yfinance as yf
    from datetime import timedelta

    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        now = datetime.now()

        pending = list(db["brain_training_data"].find({
            "price_24h_later": None,
            "tickers": {"$ne": []},
            "timestamp": {
                "$lt": now - timedelta(hours=20),
                "$gt": now - timedelta(days=7),
            }
        }).limit(50))

        updated = 0
        for doc in pending:
            tickers = doc.get("tickers", [])
            if not tickers:
                continue

            ticker = tickers[0]
            price_at = doc.get("price_at_time", 0)

            try:
                hist = yf.Ticker(ticker).history(period="3d")
                if hist.empty or not price_at:
                    continue

                current = float(hist["Close"].iloc[-1])
                change_pct = (current / price_at - 1) * 100

                strategy = doc.get("strategy", "").lower()
                content = doc.get("content", "").lower()

                outcome = "neutral"
                if "bull put" in strategy or "bull" in content:
                    outcome = "correct" if change_pct > 1 else "incorrect"
                elif "bear call" in strategy or "bear" in content:
                    outcome = "correct" if change_pct < -1 else "incorrect"
                elif "iron condor" in strategy or "condor" in content:
                    outcome = "correct" if abs(change_pct) < 3 else "incorrect"

                db["brain_training_data"].update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "price_24h_later": current,
                        "change_24h_pct":  round(change_pct, 2),
                        "outcome":         outcome,
                    }}
                )
                updated += 1

            except Exception:
                continue

        logger.info("Updated %d brain training outcomes", updated)
        return updated

    except Exception as e:
        logger.error("Update outcomes failed: %s", e)
        return 0


def get_brain_stats() -> dict:
    """Get statistics about what the brain has learned."""
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()

        total = db["brain_training_data"].count_documents({})
        by_type = {
            t: db["brain_training_data"].count_documents({"type": t})
            for t in ["chat", "scan", "alert", "image", "url", "pdf", "strategy"]
        }

        correct   = db["brain_training_data"].count_documents({"outcome": "correct"})
        incorrect = db["brain_training_data"].count_documents({"outcome": "incorrect"})
        accuracy  = round(correct / max(correct + incorrect, 1) * 100, 1)

        return {
            "total":    total,
            "by_type":  by_type,
            "correct":  correct,
            "incorrect": incorrect,
            "accuracy": accuracy,
        }
    except Exception:
        return {}
