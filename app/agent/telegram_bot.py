"""
Telegram Bot — Mobile interface for the Autonomous Trading Agent.

Commands:
    /scan    — Start a full agent run (background thread)
    /status  — VIX + market conditions snapshot
    /options — Latest 0DTE SPX iron condor setup

Notifications:
    Call notify_trade(text) from anywhere in the codebase to push
    a formatted message to your Telegram chat. The trading agent
    calls this automatically after send_options_report succeeds.

Security:
    All messages are filtered by TELEGRAM_CHAT_ID — only your chat
    can control the bot. Token and chat ID are loaded from .env only.

Usage (standalone):
    python -m app.agent.telegram_bot

Usage (integrated):
    The bot is started as a background thread by run_agent.py --daemon.
"""

import logging
import threading
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Module-level app reference so notify_trade() can reach it ─────────────
_app: Application | None = None
_scan_lock = threading.Lock()   # prevent concurrent agent runs


# ══════════════════════════════════════════════════════════════════════════════
# Auth guard — reject messages from unknown chats
# ══════════════════════════════════════════════════════════════════════════════

def _is_authorized(update: Update) -> bool:
    allowed = str(settings.TELEGRAM_CHAT_ID or "")
    if not allowed:
        logger.warning("TELEGRAM_CHAT_ID not set — all users blocked")
        return False
    return str(update.effective_chat.id) == allowed


# ══════════════════════════════════════════════════════════════════════════════
# Command handlers
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🤖 *Autonomous Trading Agent*\n\n"
        "פקודות זמינות:\n"
        "/status — בדיקת שוק (VIX + מאקרו)\n"
        "/options — הגדרת ספרד 0DTE SPX להיום\n"
        "/scan — הפעל סריקה מלאה של הסוכן (ברקע)\n",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ מושך נתוני שוק...")
    try:
        from app.services.options_service import OptionsService
        from app.services.api_hub import get_macro_context
        ctx   = OptionsService().get_market_context()
        macro = get_macro_context()
        vix   = ctx.get("vix", 0)
        spx   = ctx.get("spx_price", 0)
        fed   = macro.get("fed_rate", "N/A")
        cpi   = macro.get("cpi_yoy",  "N/A")
        regime = macro.get("regime",  "UNKNOWN")
        notes  = macro.get("notes",   "")

        if vix > 30:
            vix_emoji = "🔴"
        elif vix > 20:
            vix_emoji = "🟡"
        else:
            vix_emoji = "🟢"

        text = (
            f"📊 *סטטוס שוק — {datetime.now().strftime('%H:%M')}*\n\n"
            f"S&P 500 (SPY): `${spx:,.2f}`\n"
            f"{vix_emoji} VIX: `{vix:.1f}`\n\n"
            f"🏛️ *מאקרו*\n"
            f"ריבית פד: `{fed}%`\n"
            f"CPI שנתי: `{cpi}%`\n"
            f"משטר: `{regime}`\n"
        )
        if notes:
            text += f"_({notes})_\n"
    except Exception as exc:
        logger.exception("cmd_status failed")
        text = f"❌ שגיאה בטעינת נתוני שוק: {exc}"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ בונה ספרד 0DTE SPX...")
    try:
        from app.services.options_service import OptionsService
        svc   = OptionsService()
        ctx   = svc.get_market_context()
        setup = svc.build_0dte_spx_setup(ctx.get("vix") or 15.0)
        if not setup:
            await update.message.reply_text("⚠️ לא ניתן לבנות ספרד 0DTE — אין נתוני אופציות.")
            return
        vix = ctx.get("vix", 0)
        spy = ctx.get("spx_price", 0)
        exp = setup.get("expiry", "N/A")
        cr  = setup.get("total_credit", 0)
        sl  = setup.get("stop_loss", 0)
        pt  = setup.get("profit_target", 0)

        ps = setup.get("put_spread", {})
        cs = setup.get("call_spread", {})

        text = (
            f"🦅 *0DTE SPX Iron Condor — {exp}*\n\n"
            f"SPY: `${spy:,.2f}` | VIX: `{vix:.1f}`\n\n"
            f"📉 *Put Spread (Bull)*\n"
            f"Short: `{ps.get('short_strike','N/A')}` | Long: `{ps.get('long_strike','N/A')}`\n"
            f"Delta: `{ps.get('short_delta','N/A')}`\n\n"
            f"📈 *Call Spread (Bear)*\n"
            f"Short: `{cs.get('short_strike','N/A')}` | Long: `{cs.get('long_strike','N/A')}`\n"
            f"Delta: `{cs.get('short_delta','N/A')}`\n\n"
            f"💰 קרדיט כולל: `${cr:.2f}`\n"
            f"🎯 יעד רווח (50%): `${pt:.2f}`\n"
            f"🛑 סטופ לוס (2×): `${sl:.2f}`\n"
        )
    except Exception as exc:
        logger.exception("cmd_options failed")
        text = f"❌ שגיאה בבניית הספרד: {exc}"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    if not _scan_lock.acquire(blocking=False):
        await update.message.reply_text("⚠️ סריקה כבר פועלת ברקע — המתן לסיומה.")
        return

    await update.message.reply_text(
        "🚀 *מפעיל סריקת סוכן מלאה...*\n"
        "הסוכן יבחן מצב שוק, יסרוק מניות ויבנה אופציות.\n"
        "תקבל הודעה עם התוצאה בסיום.",
        parse_mode=ParseMode.MARKDOWN,
    )

    def _run_in_thread():
        try:
            from app.agent.trading_agent import TradingAgent
            agent   = TradingAgent()
            summary = agent.run()
            log     = agent.tool_call_log
            n_calls = len(log)
            ok      = sum(1 for e in log if "error" not in e["result"])
            result_text = (
                f"✅ *סריקה הושלמה*\n\n"
                f"כלי שהופעלו: `{n_calls}` (✓{ok} / ✗{n_calls - ok})\n\n"
                f"*סיכום:*\n{summary[:800]}"
            )
        except Exception as exc:
            logger.exception("Background agent run failed")
            result_text = f"❌ *הסריקה נכשלה*\n\n`{exc}`"
        finally:
            _scan_lock.release()

        # Send result back to Telegram
        import asyncio
        if _app:
            asyncio.run_coroutine_threadsafe(
                _app.bot.send_message(
                    chat_id=settings.TELEGRAM_CHAT_ID,
                    text=result_text,
                    parse_mode=ParseMode.MARKDOWN,
                ),
                _app.update_queue._loop if hasattr(_app.update_queue, "_loop")
                else _get_event_loop(),
            )

    threading.Thread(target=_run_in_thread, daemon=True, name="agent-scan").start()


def _get_event_loop():
    import asyncio
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


# ══════════════════════════════════════════════════════════════════════════════
# Public API — call from trading_agent or anywhere in the project
# ══════════════════════════════════════════════════════════════════════════════

def notify_trade(text: str) -> None:
    """
    Push a trade notification to the Telegram chat.

    Called automatically by the trading agent after send_options_report succeeds.
    Also usable from run_options_scan.py or run_news_scan.py.

    Example:
        notify_trade("🟢 AAPL Bull Put Spread — קרדיט $1.45 | DP 0.28")
    """
    token   = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.debug("Telegram notify skipped — token/chat_id not configured")
        return

    import requests as _req
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        _req.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        logger.info("[Telegram] Notification sent (%d chars)", len(text))
    except Exception as exc:
        logger.warning("[Telegram] notify_trade failed: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# Bot setup + run
# ══════════════════════════════════════════════════════════════════════════════

def build_app() -> Application:
    """Build and return the configured Telegram Application."""
    global _app
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("options", cmd_options))
    app.add_handler(CommandHandler("scan",    cmd_scan))
    _app = app
    return app


def run_bot() -> None:
    """Start the bot in polling mode (blocking). Called by run_agent.py --daemon."""
    logger.info("[Telegram] Bot starting (polling mode)...")
    app = build_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_bot()
