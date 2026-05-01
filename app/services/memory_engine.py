"""
memory_engine.py — MongoDB-backed persistent memory for the Trading Agent
Collections:
  chat_messages   — conversation history (TTL 30 days)
  user_profile    — Haim's profile + learning preferences
  learned_knowledge — URL / text snippets saved via /learn_url
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE = {
    "_id": "haim",
    "name": "חיים",
    "broker": "IB Israel",
    "strategies": ["Bull Put Spread", "Iron Condor", "Cash Secured Put"],
    "favorite_strategies": ["Bull Put Spread", "Iron Condor", "CSP", "0DTE"],
    "watchlist": ["NVDA", "AAPL", "TSLA", "AMZN", "SPY", "QQQ"],
    "goal": "הכנסה קבועה ממסחר באופציות",
    "risk_rules": [
        "IV Rank >= 35 → מכור פרמיה (Iron Condor / Bull Put / Bear Call)",
        "IV Rank < 25 → קנה Debit (Long Straddle / Bull Call / LEAPs)",
        "Delta ~0.20 לשורטים",
        "DTE 30-45 יום — Sweet Spot",
        "סגור ב-50% רווח / Roll ב-21 DTE",
    ],
    "mentioned_tickers": [],
    "topics_of_interest": [],
}


class MemoryEngine:
    def __init__(self):
        try:
            from app.data.mongo_client import MongoDB
            self.db = MongoDB.get_db()
            self.messages_col = self.db["chat_messages"]
            self.profile_col  = self.db["user_profile"]
            self.knowledge_col = self.db["learned_knowledge"]
            self._ensure_indexes()
        except Exception as e:
            logger.warning("MemoryEngine: DB unavailable — in-memory mode: %s", e)
            self.db            = None
            self.messages_col  = None
            self.profile_col   = None
            self.knowledge_col = None

    # ── Indexes ──────────────────────────────────────────────────────────────

    def _ensure_indexes(self):
        try:
            from pymongo import ASCENDING
            self.messages_col.create_index(
                [("timestamp", ASCENDING)],
                expireAfterSeconds=30 * 24 * 3600,
                name="ttl_30d",
                background=True,
            )
            self.knowledge_col.create_index(
                [("topic", ASCENDING)],
                unique=True,
                name="unique_topic",
                background=True,
            )
        except Exception as e:
            logger.debug("MemoryEngine index creation (non-fatal): %s", e)

    # ── Chat history ─────────────────────────────────────────────────────────

    def save_message(self, role: str, content: str, metadata: Optional[dict] = None):
        if self.messages_col is None:
            return
        try:
            doc = {
                "role": role,
                "content": content[:4000],
                "timestamp": datetime.now(timezone.utc),
            }
            if metadata:
                doc["metadata"] = metadata
            self.messages_col.insert_one(doc)
        except Exception as e:
            logger.debug("save_message failed: %s", e)

    def get_recent_messages(self, limit: int = 20) -> list:
        if self.messages_col is None:
            return []
        try:
            docs = list(
                self.messages_col
                .find({}, {"_id": 0, "role": 1, "content": 1})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return list(reversed(docs))
        except Exception as e:
            logger.debug("get_recent_messages failed: %s", e)
            return []

    def get_messages_as_claude_format(self, limit: int = 20) -> list:
        """Returns history in Claude API format: [{"role": ..., "content": ...}]"""
        msgs = self.get_recent_messages(limit)
        result = []
        for m in msgs:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant") and content:
                result.append({"role": role, "content": content})
        # Claude API requires alternating user/assistant; enforce it
        cleaned: list = []
        for msg in result:
            if cleaned and cleaned[-1]["role"] == msg["role"]:
                cleaned[-1]["content"] += "\n" + msg["content"]
            else:
                cleaned.append(dict(msg))
        return cleaned

    def clear_history(self):
        if self.messages_col is None:
            return
        try:
            result = self.messages_col.delete_many({})
            logger.info("Cleared %d chat messages", result.deleted_count)
        except Exception as e:
            logger.warning("clear_history failed: %s", e)

    # ── User profile ─────────────────────────────────────────────────────────

    def get_profile(self) -> dict:
        if self.profile_col is None:
            return dict(_DEFAULT_PROFILE)
        try:
            doc = self.profile_col.find_one({"_id": "haim"})
            if doc:
                return doc
            self.profile_col.insert_one(dict(_DEFAULT_PROFILE))
            return dict(_DEFAULT_PROFILE)
        except Exception as e:
            logger.debug("get_profile failed: %s", e)
            return dict(_DEFAULT_PROFILE)

    def update_profile(self, updates: dict):
        if self.profile_col is None:
            return
        try:
            self.profile_col.update_one(
                {"_id": "haim"},
                {"$set": updates},
                upsert=True,
            )
        except Exception as e:
            logger.debug("update_profile failed: %s", e)

    def add_mentioned_ticker(self, ticker: str):
        if self.profile_col is None:
            return
        try:
            self.profile_col.update_one(
                {"_id": "haim"},
                {"$addToSet": {"mentioned_tickers": ticker.upper()}},
                upsert=True,
            )
        except Exception as e:
            logger.debug("add_mentioned_ticker failed: %s", e)

    def add_to_watchlist(self, ticker: str):
        if self.profile_col is None:
            return
        try:
            self.profile_col.update_one(
                {"_id": "haim"},
                {"$addToSet": {"watchlist": ticker.upper()}},
                upsert=True,
            )
        except Exception as e:
            logger.debug("add_to_watchlist failed: %s", e)

    def add_topic_of_interest(self, topic: str):
        if self.profile_col is None:
            return
        try:
            self.profile_col.update_one(
                {"_id": "haim"},
                {"$addToSet": {"topics_of_interest": topic}},
                upsert=True,
            )
        except Exception as e:
            logger.debug("add_topic_of_interest failed: %s", e)

    # ── Learned knowledge ─────────────────────────────────────────────────────

    def save_knowledge(self, topic: str, content: str, source: str = ""):
        if self.knowledge_col is None:
            return
        try:
            self.knowledge_col.update_one(
                {"topic": topic},
                {
                    "$set": {
                        "content": content[:3000],
                        "source": source,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
            logger.info("Knowledge saved: %s", topic)
        except Exception as e:
            logger.debug("save_knowledge failed: %s", e)

    def get_relevant_knowledge(self, query: str, limit: int = 3) -> list:
        if self.knowledge_col is None:
            return []
        try:
            words = [w for w in re.split(r"\W+", query.upper()) if len(w) > 2]
            if not words:
                return []
            pattern = "|".join(re.escape(w) for w in words[:6])
            docs = list(
                self.knowledge_col.find(
                    {"topic": {"$regex": pattern, "$options": "i"}},
                    {"_id": 0, "topic": 1, "content": 1},
                ).limit(limit)
            )
            return docs
        except Exception as e:
            logger.debug("get_relevant_knowledge failed: %s", e)
            return []

    def list_knowledge(self) -> list:
        if self.knowledge_col is None:
            return []
        try:
            return list(
                self.knowledge_col.find(
                    {}, {"_id": 0, "topic": 1, "source": 1, "updated_at": 1}
                ).sort("updated_at", -1)
            )
        except Exception as e:
            logger.debug("list_knowledge failed: %s", e)
            return []

    # ── System prompt builder ─────────────────────────────────────────────────

    def build_system_prompt(self) -> str:
        profile   = self.get_profile()
        name      = profile.get("name", "חיים")
        broker    = profile.get("broker", "IB Israel")
        strats    = ", ".join(profile.get("favorite_strategies", profile.get("strategies", [])))
        watchlist = ", ".join(profile.get("watchlist", [])[:10]) or "—"
        goal      = profile.get("goal", "הכנסה קבועה ממסחר באופציות")
        rules     = "\n".join(f"  • {r}" for r in profile.get("risk_rules", []))
        tickers   = ", ".join(profile.get("mentioned_tickers", [])[-10:]) or "—"

        knowledge_items   = self.list_knowledge()
        knowledge_section = ""
        if knowledge_items:
            topics = ", ".join(k["topic"] for k in knowledge_items[:10])
            knowledge_section = f"\n\nידע שנלמד מ-URLs / טקסטים: {topics}"

        return (
            f"אתה סוכן מסחר AI אישי של {name}. תמיד ענה בעברית.\n"
            f"מתמחה: Options trading, Tastytrade methodology.\n"
            f"ברוקר: {broker}.\n"
            f"אסטרטגיות מועדפות: {strats}.\n"
            f"מניות במעקב: {watchlist}.\n"
            f"מטרה: {goal}.\n\n"
            f"חוקים קשיחים:\n{rules}\n\n"
            f"מניות שנזכרו לאחרונה: {tickers}"
            f"{knowledge_section}\n\n"
            "כשמזכירים טיקר — הבא IV Rank + Trend + המלצת אסטרטגיה.\n"
            "אסור: Naked Call / Naked Put (סיכון בלתי מוגבל).\n"
            "המטרה: $1,000 שבועי קבוע מ-Options בשיטת Tastytrade."
        )
