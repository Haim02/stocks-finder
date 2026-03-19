"""
Telegram Bot — Mobile interface for the Autonomous Trading Agent.

Commands:
    /scan           — Start a full agent run (background thread)
    /status         — VIX + market conditions snapshot
    /options        — Latest 0DTE SPX iron condor setup
    /analyze TICKER — Deep Dive research report (email + Telegram summary)

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
        "/scan — סריקת חדשות + טכני (שני מקורות)\n"
        "   `/scan finviz` — Finviz בלבד\n"
        "   `/scan tv` — TradingView בלבד\n"
        "   `/scan both` — שניהם (ברירת מחדל)\n"
        "/analyze TICKER — ניתוח עמוק למניה ספציפית\n"
        "   _דוגמה: /analyze AAPL_\n",
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


_VALID_SOURCES = {"finviz", "tv", "both"}
_SOURCE_LABEL  = {
    "finviz": "Finviz בלבד",
    "tv":     "TradingView בלבד",
    "both":   "Finviz + TradingView (מיזוג)",
}


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /scan [finviz|tv|both]

    Runs the hybrid news + technical scan via run_news_scan.run_hybrid_scan().
      /scan          → both sources (default)
      /scan finviz   → Finviz only
      /scan tv       → TradingView only (requires Selenium/Chrome)
      /scan both     → explicit merge of both
    """
    if not _is_authorized(update):
        return

    # Parse optional source argument
    raw_args = context.args
    if raw_args:
        source = raw_args[0].lower()
        if source not in _VALID_SOURCES:
            await update.message.reply_text(
                f"⚠️ מקור לא תקין: `{source}`\n"
                f"אפשרויות: `finviz` \\| `tv` \\| `both`",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
    else:
        source = "both"

    if not _scan_lock.acquire(blocking=False):
        await update.message.reply_text("⚠️ סריקה כבר פועלת ברקע — המתן לסיומה.")
        return

    label = _SOURCE_LABEL[source]
    await update.message.reply_text(
        f"🔍 *מפעיל סריקת חדשות — {label}*\n"
        f"סורק מניות, מנתח חדשות ומשקלל AI...\n"
        f"תקבל דוח במייל ✉️ ועדכון כאן בסיום.",
        parse_mode=ParseMode.MARKDOWN,
    )

    def _run_news_scan():
        try:
            from run_news_scan import run_hybrid_scan
            summary = run_hybrid_scan(source=source)
            notify_trade(f"📰 *{label} — הושלמה*\n\n{summary}")
        except Exception as exc:
            logger.exception("[Telegram] News scan (%s) failed", source)
            notify_trade(f"❌ *סריקה נכשלה ({source})*\n`{exc}`")
        finally:
            _scan_lock.release()

    threading.Thread(
        target=_run_news_scan,
        daemon=True,
        name=f"news-scan-{source}",
    ).start()


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /analyze TICKER — runs a Deep Dive analysis in a background thread.

    Flow:
      1. Immediate reply: "Starting deep dive on {TICKER}..."
      2. Background thread:
           a. AnalysisService.analyze(ticker)        — collect all data
           b. AIService.get_deep_dive_analysis()     — Goldman Sachs note
           c. EmailService.send_deep_dive_report()   — HTML email via Resend
           d. notify_trade(summary)                  — short Telegram message
    """
    if not _is_authorized(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ נא לציין טיקר\\.  דוגמה: `/analyze AAPL`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    ticker = args[0].upper().strip()

    # Validate: basic ticker format
    if not ticker.isalpha() or len(ticker) > 10:
        await update.message.reply_text(f"⚠️ טיקר לא תקין: `{ticker}`", parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(
        f"🔬 *מתחיל ניתוח עמוק על {ticker}...*\n\n"
        f"אאסוף נתונים פונדמנטליים, טכניים וחדשות.\n"
        f"הדוח המלא יישלח במייל ✉️ ואני אשלח לך סיכום כאן בסיום.",
        parse_mode=ParseMode.MARKDOWN,
    )

    def _run_deep_dive():
        try:
            from app.services.analysis_service import AnalysisService
            from app.services.ai_service import AIService
            from app.services.email_service import EmailService

            # 1. Collect all data
            logger.info("[Telegram] Deep dive started: %s", ticker)
            data = AnalysisService().analyze(ticker)

            # 2. AI Goldman Sachs analysis
            ai_result = AIService().get_deep_dive_analysis(ticker, data)

            # 3. Email the full HTML report
            EmailService.send_deep_dive_report(data, ai_result)

            # 4. Send short Telegram summary
            score  = ai_result.get("score", 0)
            rec    = ai_result.get("recommendation", "HOLD")
            price  = data.get("current_price", "N/A")
            rsi    = data.get("rsi", "N/A")
            trend  = data.get("trend_status", "")

            emoji = "🟢" if rec == "BUY" else "🔴" if rec == "SELL" else "🟡"
            summary = (
                f"{emoji} *{ticker} — Deep Dive הושלם*\n\n"
                f"💰 מחיר: `${price}`\n"
                f"📊 RSI: `{rsi}` | {trend}\n"
                f"🎯 המלצה: *{rec}* | ציון: `{score}/100`\n\n"
                f"📧 הדוח המלא נשלח למייל שלך."
            )
            notify_trade(summary)
            logger.info("[Telegram] Deep dive complete: %s score=%d rec=%s", ticker, score, rec)

        except Exception as exc:
            logger.exception("[Telegram] Deep dive failed for %s", ticker)
            notify_trade(f"❌ *ניתוח עמוק נכשל עבור {ticker}*\n\n`{exc}`")

    threading.Thread(
        target=_run_deep_dive,
        daemon=True,
        name=f"deep-dive-{ticker}",
    ).start()


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
    app.add_handler(CommandHandler("analyze", cmd_analyze))
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
