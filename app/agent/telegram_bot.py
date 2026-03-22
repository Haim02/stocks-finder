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
        "/options — ספרד 0DTE SPX Iron Condor להיום\n"
        "/scan — סריקת חדשות + טכני\n"
        "   `/scan finviz` · `/scan tv` · `/scan both`\n"
        "/analyze TICKER — ניתוח Goldman Sachs + דוח מייל\n"
        "/strategies [TICKERS] — מנוע אסטרטגיות מלא\n"
        "/quick_scan — סיכום מהיר: Ticker | Strategy | PoP | Income\n"
        "/trade_check TICKER — ניתוח IV + מגמה + המלצת Wheel/Spread\n",
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


async def cmd_strategies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /strategies [TICKER1 TICKER2 ...]

    Run the multi-strategy options engine. Without args: scans top Finviz gainers/losers.
    With args: analyze specific tickers only (max 8).
    """
    if not _is_authorized(update):
        return

    args = context.args
    await update.message.reply_text("⏳ מריץ מנוע אסטרטגיות אופציות...")

    try:
        from app.services.options_strategy_engine import OptionsStrategyEngine
        from app.services.iv_calculator import get_iv_rank, get_vix_level, check_earnings_soon
        import yfinance as yf

        engine    = OptionsStrategyEngine()
        vix       = get_vix_level()
        results   = []

        if args:
            tickers = [t.upper() for t in args[:8]]
        else:
            from app.services.finviz_service import FinvizService
            tickers = FinvizService.get_bullish_tickers(n=6) + FinvizService.get_bearish_tickers(n=4)

        for ticker in tickers[:10]:
            try:
                price = yf.Ticker(ticker).fast_info.last_price
                if not price:
                    continue
                iv_rank  = get_iv_rank(ticker)
                earnings = check_earnings_soon(ticker)
                # Try neutral first; if no signal try bullish/bearish
                for trend in ("neutral", "bullish", "bearish", "strong_bullish", "strong_bearish"):
                    signal = engine.select_strategy(
                        ticker=ticker, price=price, trend=trend,
                        iv_rank=iv_rank, rsi=50.0, vix_level=vix,
                        has_earnings_soon=earnings,
                    )
                    if signal:
                        results.append(signal)
                        break
            except Exception:
                continue

        if not results:
            await update.message.reply_text("⚠️ לא נמצאו אותות אסטרטגיה כעת.")
            return

        for signal in results:
            msg = engine.format_telegram_message(signal)
            try:
                await update.message.reply_text(msg, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(msg)

    except Exception as exc:
        logger.exception("cmd_strategies failed")
        await update.message.reply_text(f"❌ שגיאה במנוע אסטרטגיות: {exc}")


async def cmd_quick_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /quick_scan

    Returns a compact summary: Ticker | Strategy | PoP% | Est. Income
    for the top opportunities right now.
    """
    if not _is_authorized(update):
        return

    await update.message.reply_text("⚡ סריקה מהירה...")

    try:
        from app.services.options_strategy_engine import OptionsStrategyEngine
        from app.services.iv_calculator import get_iv_rank, get_vix_level, check_earnings_soon
        from app.services.finviz_service import FinvizService
        import yfinance as yf

        engine  = OptionsStrategyEngine()
        vix     = get_vix_level()
        bull    = FinvizService.get_bullish_tickers(n=8)
        bear    = FinvizService.get_bearish_tickers(n=8)
        rows    = []

        for ticker, trend_hint in [(t, "bullish") for t in bull] + [(t, "bearish") for t in bear]:
            try:
                price = yf.Ticker(ticker).fast_info.last_price
                if not price:
                    continue
                iv_rank  = get_iv_rank(ticker)
                earnings = check_earnings_soon(ticker)
                signal   = engine.select_strategy(
                    ticker=ticker, price=price, trend=trend_hint,
                    iv_rank=iv_rank, rsi=50.0, vix_level=vix,
                    has_earnings_soon=earnings,
                )
                if signal:
                    income = (
                        f"+${signal.net_credit:.2f}"
                        if signal.net_credit > 0
                        else f"-${signal.net_debit:.2f}"
                    )
                    cat = "🟢" if signal.category == "BULLISH" else ("🔴" if signal.category == "BEARISH" else "⚪")
                    rows.append(
                        f"{cat} `{ticker:<6}` | {signal.strategy_display:<22} | "
                        f"PoP: `{signal.probability_of_profit:.0f}%` | `{income}`"
                    )
            except Exception:
                continue

        if not rows:
            await update.message.reply_text("⚠️ אין הזדמנויות פעילות כרגע.")
            return

        header = (
            f"⚡ *Quick Scan — {len(rows)} הזדמנויות*\n"
            f"VIX: `{vix:.1f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        await update.message.reply_text(
            header + "\n".join(rows),
            parse_mode="Markdown",
        )

    except Exception as exc:
        logger.exception("cmd_quick_scan failed")
        await update.message.reply_text(f"❌ שגיאה בסריקה מהירה: {exc}")


async def cmd_trade_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /trade_check TICKER

    Deep dive: IV Rank, earnings date, technicals → recommend best Wheel or Spread entry.
    """
    if not _is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ נא לציין טיקר\\.  דוגמה: `/trade_check AAPL`",
            parse_mode="Markdown",
        )
        return

    ticker = context.args[0].upper().strip()
    if not ticker.isalpha() or len(ticker) > 10:
        await update.message.reply_text(f"⚠️ טיקר לא תקין: `{ticker}`", parse_mode="Markdown")
        return

    await update.message.reply_text(f"🔎 בודק {ticker}...")

    try:
        from app.services.options_strategy_engine import OptionsStrategyEngine
        from app.services.iv_calculator import (
            get_iv_rank, get_current_iv, get_vix_level,
            check_earnings_soon, get_nearest_expiry,
        )
        import yfinance as yf

        stock   = yf.Ticker(ticker)
        price   = stock.fast_info.last_price
        if not price:
            await update.message.reply_text(f"⚠️ לא ניתן לטעון מחיר עבור `{ticker}`")
            return

        iv_rank  = get_iv_rank(ticker)
        curr_iv  = get_current_iv(ticker)
        earnings = check_earnings_soon(ticker, days=14)
        vix      = get_vix_level()
        expiry   = get_nearest_expiry(ticker, 35)

        # Pull quick technicals
        hist  = stock.history(period="3mo")
        close = hist["Close"] if not hist.empty else None
        sma50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if close is not None and len(close) >= 50 else None
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = round(100 - 100 / (1 + gain.iloc[-1] / max(loss.iloc[-1], 1e-9)), 1) if close is not None and len(close) >= 14 else 50.0

        if sma50 and price > sma50 * 1.02:
            trend = "bullish"
        elif sma50 and price < sma50 * 0.98:
            trend = "bearish"
        else:
            trend = "neutral"

        engine = OptionsStrategyEngine()
        best   = None
        for t in (trend, "neutral", "bullish", "bearish"):
            sig = engine.select_strategy(
                ticker=ticker, price=price, trend=t,  # type: ignore[arg-type]
                iv_rank=iv_rank, rsi=rsi, vix_level=vix,
                has_earnings_soon=earnings,
            )
            if sig:
                best = sig
                break

        # Summary header
        iv_bar  = "🔥" * min(5, int(iv_rank / 20))
        rsi_tag = "🟢 Oversold" if rsi < 35 else ("🔴 Overbought" if rsi > 65 else "🟡 Neutral")
        header  = (
            f"🔎 *Trade Check — {ticker}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Price: `${price:.2f}`\n"
            f"📊 IV Rank: `{iv_rank:.0f}%` {iv_bar}\n"
            f"📈 Current IV: `{curr_iv * 100:.1f}%`\n"
            f"📐 RSI(14): `{rsi:.1f}` — {rsi_tag}\n"
            f"📉 Trend vs SMA50: `{trend.upper()}`\n"
            f"📅 Nearest expiry: `{expiry}`\n"
            f"⚠️ Earnings soon (<14d): `{'YES' if earnings else 'No'}`\n"
            f"🌡️ VIX: `{vix:.1f}`\n\n"
        )

        if best:
            msg = header + engine.format_telegram_message(best)
        else:
            msg = header + (
                f"_לא זוהה אות ברור עבור {ticker} כרגע._\n\n"
                f"💡 *המלצה:* המתן לסיגנל ברור יותר.\n"
                f"IVR נוכחי: {iv_rank:.0f}% — "
                + ("שוק גבוה, המתן לירידה לפני כניסה" if iv_rank > 60 else
                   "IVR נמוך — עדיף ספרד דביט אם יש מגמה")
            )

        try:
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(msg)

    except Exception as exc:
        logger.exception("cmd_trade_check failed for %s", ticker)
        await update.message.reply_text(f"❌ שגיאה ב-trade check עבור {ticker}: {exc}")


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
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("status",       cmd_status))
    app.add_handler(CommandHandler("options",      cmd_options))
    app.add_handler(CommandHandler("scan",         cmd_scan))
    app.add_handler(CommandHandler("analyze",      cmd_analyze))
    app.add_handler(CommandHandler("strategies",   cmd_strategies))
    app.add_handler(CommandHandler("quick_scan",   cmd_quick_scan))
    app.add_handler(CommandHandler("trade_check",  cmd_trade_check))
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
