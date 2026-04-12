"""
free_chat.py — Free Conversation Handler for Telegram Bot
==========================================================

Replaces rigid /commands with natural Hebrew conversation powered by Claude.
Reads MEMORY.md and CLAUDE.md as system prompt so the agent always knows
who Haim is, the trading rules, and the project context.

Features:
- Natural Hebrew conversation with Claude (claude-sonnet-4-5)
- Per-user conversation history (last 20 messages, rolling window)
- /learn <text> → summarizes and appends to MEMORY.md
- /reset → clears conversation history
- Smart scan intent detection → redirects to /scan command
"""

import logging
import os
import re
from pathlib import Path
from collections import deque

import anthropic
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
CLAUDE_MODEL  = "claude-sonnet-4-5"
MAX_HISTORY   = 20
MAX_TOKENS    = 1024

# Paths — go up from app/agent/ to project root
_ROOT        = Path(__file__).parent.parent.parent
MEMORY_PATH  = _ROOT / "MEMORY.md"
CLAUDE_PATH  = _ROOT / "CLAUDE.md"

SCAN_INTENTS = [
    "תריץ סריקה", "תעשה סריקה", "סרוק", "run scan",
    "תריץ אופציות", "תשלח דוח", "תפעיל",
]


# ── System Prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    parts = []
    if CLAUDE_PATH.exists():
        parts.append(CLAUDE_PATH.read_text(encoding="utf-8"))
    else:
        parts.append(
            "You are an autonomous options trading AI agent for Haim. "
            "Always respond in Hebrew. Financial terms stay in English."
        )
    if MEMORY_PATH.exists():
        parts.append("\n\n---\n\n## FULL MEMORY\n\n")
        parts.append(MEMORY_PATH.read_text(encoding="utf-8"))

    parts.append(
        "\n\n---\n\n"
        "## CONVERSATION RULES\n"
        "- Always respond in Hebrew\n"
        "- Financial/technical terms stay in English (IV, Delta, Strike, DTE, etc.)\n"
        "- Be direct and analytical — numbers first, no fluff\n"
        "- Address the user as חיים\n"
        "- Keep answers concise for Telegram — bullet points, not walls of text\n"
        "- Use emojis sparingly (📊 for data, ⚠️ for risk, ✅ for confirmation)\n"
        "- Never suggest Naked options (undefined risk)\n"
        "- Always back recommendations with IV Rank + Trend data\n"
    )
    return "".join(parts)


# ── Conversation Memory ───────────────────────────────────────────────────────

class ConversationMemory:
    def __init__(self):
        self._histories: dict[int, deque] = {}

    def get(self, user_id: int) -> list[dict]:
        return list(self._histories.get(user_id, deque(maxlen=MAX_HISTORY)))

    def add(self, user_id: int, role: str, content: str):
        if user_id not in self._histories:
            self._histories[user_id] = deque(maxlen=MAX_HISTORY)
        self._histories[user_id].append({"role": role, "content": content})

    def reset(self, user_id: int):
        self._histories.pop(user_id, None)


# ── Main Handler ──────────────────────────────────────────────────────────────

class FreeChatHandler:
    """
    Handles all non-command Telegram messages as free conversation with Claude.

    Add to telegram_bot.py:
        from app.agent.free_chat import FreeChatHandler
        _free_chat = FreeChatHandler()

        async def free_chat_handler(update, context):
            await _free_chat.handle(update, context)

        # Register LAST (after all CommandHandlers):
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_chat_handler))
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._memory = ConversationMemory()
        self._system_prompt = _build_system_prompt()
        logger.info("FreeChatHandler initialized (model=%s)", CLAUDE_MODEL)

    def reload_memory(self):
        self._system_prompt = _build_system_prompt()
        logger.info("System prompt reloaded from MEMORY.md")

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        text = update.message.text.strip()

        if text.lower() == "/reset":
            self._memory.reset(user_id)
            await update.message.reply_text("🔄 השיחה אופסה. נתחיל מחדש, חיים.")
            return

        if text.lower().startswith("/learn"):
            await self._handle_learn(update, text)
            return

        if any(kw in text.lower() for kw in SCAN_INTENTS):
            await update.message.reply_text(
                "📊 כדי להריץ סריקה, השתמש בפקודה /scan\n"
                "אני אשלח לך את התוצאות ברגע שהסריקה תסתיים."
            )
            return

        await self._handle_chat(update, user_id, text)

    async def _handle_chat(self, update: Update, user_id: int, text: str) -> None:
        await update.message.chat.send_action(ChatAction.TYPING)
        self._memory.add(user_id, "user", text)

        # Check if question needs real-time data → enrich with Perplexity
        perplexity_context = ""
        if _needs_realtime_data(text):
            try:
                from app.services.perplexity_service import PerplexityService
                pplx = PerplexityService()
                if pplx.is_available():
                    answer = pplx.ask(text)
                    if answer:
                        perplexity_context = f"\n\n[Real-time data from Perplexity]:\n{answer}"
                        logger.info("Perplexity enriched free chat response")
            except Exception as e:
                logger.warning("Perplexity enrichment failed: %s", e)

        # Build messages with optional Perplexity context injected into last user turn
        messages = self._memory.get(user_id)
        if perplexity_context:
            messages = messages[:-1] + [{
                "role": "user",
                "content": text + perplexity_context,
            }]

        try:
            response = self._client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                system=self._system_prompt,
                messages=messages,
            )
            reply = response.content[0].text
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            reply = "⚠️ שגיאה בחיבור ל-AI. נסה שוב בעוד רגע."

        self._memory.add(user_id, "assistant", reply)
        for chunk in _split_message(reply):
            await update.message.reply_text(chunk, parse_mode="Markdown")

    async def _handle_learn(self, update: Update, text: str) -> None:
        content = text[len("/learn"):].strip()

        if not content:
            await update.message.reply_text(
                "📚 *שימוש:* `/learn <טקסט>`\n\nהדבק את הטקסט שאתה רוצה שאלמד.",
                parse_mode="Markdown",
            )
            return

        if re.match(r"https?://", content):
            await update.message.reply_text(
                "🔗 זיהיתי קישור. כרגע אני לא גולש לאתרים ישירות.\n"
                "העתק את הטקסט מהמאמר והדבק אותו עם /learn"
            )
            return

        await update.message.chat.send_action(ChatAction.TYPING)
        try:
            resp = self._client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=400,
                system=(
                    "You are a knowledge extractor for an options trading AI agent. "
                    "Summarize the following into concise bullet points capturing "
                    "trading insights, rules, or facts. "
                    "Keep financial terms in English. Output in Hebrew."
                ),
                messages=[{"role": "user", "content": content}],
            )
            summary = resp.content[0].text
        except Exception as e:
            logger.error("Summary error: %s", e)
            summary = content

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n\n---\n\n## 📚 נלמד ב-{timestamp}\n\n{summary}\n"

        try:
            with open(MEMORY_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
            self.reload_memory()
            await update.message.reply_text(
                f"✅ למדתי! הוספתי לזיכרון שלי.\n\n*סיכום:*\n{summary[:400]}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("Failed to write MEMORY.md: %s", e)
            await update.message.reply_text("⚠️ שגיאה בשמירת הידע.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _needs_realtime_data(text: str) -> bool:
    """Detect if the question needs real-time web data from Perplexity."""
    keywords = [
        "היום", "עכשיו", "כרגע", "אמר", "הודיע", "חדשות", "דוח",
        "פד", "fed", "fomc", "earnings", "דוחות",
        "today", "now", "latest", "breaking", "just",
        "what happened", "מה קרה", "מה נאמר",
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current, current_len = [], [], 0
    for para in text.split("\n\n"):
        if current_len + len(para) + 2 > limit:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks
