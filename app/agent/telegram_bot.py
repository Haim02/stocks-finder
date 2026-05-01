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

import asyncio
import logging
import threading
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.core.config import settings
from app.agent.free_chat import get_agent, split_message

logger = logging.getLogger(__name__)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free text messages via TradingAgent (photos/docs have dedicated handlers)."""
    if not _is_authorized(update):
        return

    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    agent = get_agent()

    # /learn and /learn_url typed as free text (not command)
    if user_text.lower().startswith("/learn"):
        reply = await agent.handle_learn(user_text)
        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)
        return

    reply = await agent.handle_message(text=user_text)

    for chunk in split_message(reply):
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(chunk)

# ── Conversation states ───────────────────────────────────────────────────────
GEX_WAITING_TICKER = 1   # /gex: waiting for user to type ticker name

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


async def cmd_options_0dte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /options — Show current SPX 0DTE Iron Condor setup.
    Falls back to theoretical setup when live data is unavailable
    (outside market hours or yfinance data gap).
    """
    if not _is_authorized(update):
        return
    await update.message.reply_text("⏳ בונה ספרד 0DTE SPX...")
    try:
        result = await asyncio.to_thread(_run_options_0dte_sync)
        await update.message.reply_text(result, parse_mode="Markdown")
    except Exception as exc:
        logger.exception("cmd_options_0dte failed")
        await update.message.reply_text(
            f"❌ שגיאה בבניית ספרד 0DTE: {exc}\n"
            f"💡 נסה שוב במהלך שעות המסחר (15:30–22:00 שעון ישראל)"
        )


def _run_options_0dte_sync() -> str:
    """
    Build 0DTE SPX Iron Condor setup.
    Primary: live data from OptionsService.
    Fallback: theoretical setup based on current SPY price + VIX.
    """
    import yfinance as yf
    from app.services.iv_calculator import get_vix_level

    vix = get_vix_level()

    # ── Try live OptionsService first ─────────────────────────────────────
    try:
        from app.services.options_service import OptionsService
        svc    = OptionsService()
        report = svc.build_report([], [])   # empty lists = SPX only
        spx    = report.get("spx_setup")

        if spx:
            put_sell  = spx.get("put_sell",  "N/A")
            put_buy   = spx.get("put_buy",   "N/A")
            call_sell = spx.get("call_sell", "N/A")
            call_buy  = spx.get("call_buy",  "N/A")
            credit    = spx.get("credit",    0)
            max_loss  = spx.get("max_loss",  0)
            rr        = spx.get("risk_reward", 0)
            spy_price = report.get("spx_price", "N/A")

            return (
                f"🦅 *Iron Condor 0DTE — SPX*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💹 SPY: ${spy_price} | VIX: {vix:.1f}\n\n"
                f"📐 *מבנה העסקה:*\n"
                f"   מכור Put  ${put_sell} / קנה Put  ${put_buy}\n"
                f"   מכור Call ${call_sell} / קנה Call ${call_buy}\n\n"
                f"💰 *מטריקות:*\n"
                f"   קרדיט: ${credit:.2f} | הפסד מקס: ${max_loss:.2f}\n"
                f"   יחס R/R: {rr:.2f}\n\n"
                f"🏁 *כללי ניהול:*\n"
                f"   סגור ב-50% רווח\n"
                f"   Stop-loss: 2x הקרדיט\n"
                f"   כניסה: 9:45–10:30 ET\n\n"
                f"⚠️ _0DTE בלבד — פקיעה היום!_"
            )
    except Exception as e:
        logger.warning("OptionsService failed: %s — using fallback", e)

    # ── Fallback: theoretical setup ────────────────────────────────────────
    try:
        spy_price = yf.Ticker("SPY").fast_info.last_price or 500.0
    except Exception:
        spy_price = 500.0

    width     = 5.0 if vix <= 20 else 3.0
    put_sell  = round(spy_price * 0.993)
    put_buy   = round(put_sell - width)
    call_sell = round(spy_price * 1.007)
    call_buy  = round(call_sell + width)
    credit_est = round(width * 0.30, 2)
    max_loss   = round((width - credit_est) * 100, 2)
    rr_est     = round((credit_est * 100) / max_loss, 2) if max_loss > 0 else 0
    vix_label  = "גבוה ⚠️" if vix > 25 else ("בינוני" if vix > 18 else "נמוך ✅")

    return (
        f"🦅 *Iron Condor 0DTE — SPX (תיאורטי)*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💹 SPY: ~${spy_price:.0f} | VIX: {vix:.1f} ({vix_label})\n\n"
        f"📐 *מבנה מוצע:*\n"
        f"   מכור Put  ${put_sell} / קנה Put  ${put_buy}\n"
        f"   מכור Call ${call_sell} / קנה Call ${call_buy}\n\n"
        f"💰 *הערכת מטריקות:*\n"
        f"   קרדיט משוער: ~${credit_est} | הפסד מקס: ~${max_loss:.0f}\n"
        f"   יחס R/R: ~{rr_est}\n\n"
        f"🏁 *כללי ניהול:*\n"
        f"   סגור ב-50% רווח\n"
        f"   Stop-loss: 2x הקרדיט\n"
        f"   כניסה: 9:45–10:30 ET\n\n"
        f"⚠️ _נתונים תיאורטיים — אין נתוני אופציות חיים כרגע._\n"
        f"💡 _הרץ שוב במהלך שעות המסחר לנתונים מדויקים._"
    )


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

    Run the multi-strategy options engine.
    Without args: scans S&P 500 + Nasdaq 100, rotated daily.
    With args: analyze specific tickers only (max 15).
    """
    if not _is_authorized(update):
        return

    args        = list(context.args) if context.args else []
    source_desc = " ".join(args).upper() if args else "S&P 500 + Nasdaq 100"

    await update.message.reply_text(
        f"🎯 *סריקת אסטרטגיות אופציות*\n\n"
        f"📊 מקור מניות: {source_desc}\n"
        f"🔄 מסנן לפי: IV Rank, RSI, גרף, חדשות, DB\n"
        f"⏳ אנא המתן...",
        parse_mode="Markdown",
    )

    try:
        messages = await asyncio.to_thread(_run_strategies_sync, args)
        if not messages:
            await update.message.reply_text(
                "📊 לא נמצאו איתותי אסטרטגיה עכשיו.\n"
                "💡 כל המניות בצינון 5 ימים או אין תנאים מתאימים.",
            )
            return
        for msg in messages:
            try:
                await update.message.reply_text(msg, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(msg)
    except Exception as exc:
        logger.exception("cmd_strategies failed")
        await update.message.reply_text(f"❌ שגיאה במנוע אסטרטגיות: {exc}")


def _log_ticker_for_training(ticker: str, price: float, strategy_name: str) -> None:
    """Fire-and-forget: log this ticker to training_events for future XGBoost labeling."""
    try:
        from app.services.training_logger import log_training_event
        from app.services.ml_service import predict_confidence
        xgb_conf = predict_confidence(ticker)
        log_training_event(
            ticker=ticker,
            source="strategies_bot",
            price=price,
            xgb_conf=xgb_conf,
            strategy_name=strategy_name,
        )
    except Exception:
        logger.debug("_log_ticker_for_training failed for %s", ticker, exc_info=True)


def _run_strategies_sync(args: list) -> list[str]:
    """
    Returns list of formatted Telegram messages, one per signal.

    Ticker source:
    - Default (no args): S&P 500 + Nasdaq 100, rotated daily (index_universe.py)
    - With args: specific tickers provided by user

    Pipeline:
    1. Build ticker list from index universe (or user args)
    2. Apply 5-day cooldown filter
    3. Score with XGBoost → top 20
    4. For each: RSI, chart patterns, finvizfinance context, news sentiment, strategy
    """
    import yfinance as yf
    from app.services.options_strategy_engine import OptionsStrategyEngine
    from app.services.iv_calculator import get_iv_rank, get_vix_level, check_earnings_soon
    from app.data.mongo_client import MongoDB

    engine        = OptionsStrategyEngine()
    vix           = get_vix_level()
    messages: list[str] = []
    COOLDOWN_DAYS = 5

    # ── Ticker normalization ──────────────────────────────────────────────
    TICKER_MAP = {
        "SPX": "SPY", "^SPX": "SPY", "^GSPC": "SPY",
        "NDX": "QQQ", "^NDX": "QQQ",
        "RUT": "IWM", "^RUT": "IWM",
        "DJI": "DIA", "^DJI": "DIA",
    }

    def normalize(t: str) -> str:
        return TICKER_MAP.get(t.upper(), t.upper())

    # ── STEP A: Build ticker list ─────────────────────────────────────────
    if args:
        tickers_raw   = [normalize(t) for t in args[:15]]
        skip_cooldown = True
        logger.info("[STRATEGIES] Manual tickers: %s", tickers_raw)
    else:
        try:
            from app.services.index_universe import get_daily_candidates
            tickers_raw = get_daily_candidates(n=40, include_sp500=True, include_nasdaq=True)
            logger.info("[STRATEGIES] Index universe: %d candidates", len(tickers_raw))
        except Exception as e:
            logger.warning("[STRATEGIES] Index universe failed: %s — using fallback", e)
            import random
            fallback = [
                "AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA", "AMD",
                "JPM", "V", "MA", "BAC", "XOM", "CVX", "JNJ", "PFE", "HD", "MCD",
                "NFLX", "COST", "AVGO", "QCOM", "ADBE", "CRM", "INTC", "ORCL",
            ]
            random.shuffle(fallback)
            tickers_raw = fallback[:30]
        skip_cooldown = False

    # ── STEP B: Cooldown filter ───────────────────────────────────────────
    tickers_to_scan: list[str] = []
    for ticker in tickers_raw:
        if skip_cooldown:
            tickers_to_scan.append(ticker)
        else:
            try:
                if not MongoDB.was_strategy_sent_recently(ticker, days=COOLDOWN_DAYS):
                    tickers_to_scan.append(ticker)
            except Exception:
                tickers_to_scan.append(ticker)   # include if check fails

    logger.info("[STRATEGIES] After cooldown: %d tickers", len(tickers_to_scan))

    # ── STEP C: XGBoost scoring → top 20 ─────────────────────────────────
    try:
        from app.services.ml_service import predict_confidence
        scored: list[tuple[float, str]] = []
        for t in tickers_to_scan:
            conf = predict_confidence(t)
            scored.append((conf if conf is not None else 0.0, t))
        scored.sort(reverse=True)
        tickers_to_scan = [t for _, t in scored[:20]]
        logger.info("[STRATEGIES] XGBoost top-20: %s", tickers_to_scan[:5])
    except Exception:
        tickers_to_scan = tickers_to_scan[:20]

    # ── STEP D: Analyze each ticker ───────────────────────────────────────
    for ticker in tickers_to_scan:
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if not price or price <= 0:
                continue

            # RSI(14)
            rsi_val = 50.0
            try:
                hist = stock.history(period="2mo")
                if len(hist) >= 14:
                    delta   = hist["Close"].diff()
                    gain    = delta.clip(lower=0).rolling(14).mean()
                    loss    = (-delta.clip(upper=0)).rolling(14).mean()
                    rsi_val = float((100 - 100 / (1 + gain / loss)).iloc[-1])
            except Exception:
                pass

            # IV + earnings
            try:
                iv_rank = get_iv_rank(ticker)
            except Exception:
                iv_rank = 50.0

            try:
                earnings = check_earnings_soon(ticker, days=7)
            except Exception:
                earnings = False

            # ── Chart patterns (TA) ───────────────────────────────────────
            base_trend = "neutral"
            chart: dict = {}
            try:
                from app.ta.chart_patterns import analyze_chart
                hist_3mo = stock.history(period="3mo")
                chart    = analyze_chart(ticker, hist_3mo)
                if chart.get("is_sideways"):
                    base_trend = "neutral"
                elif chart.get("trend_override"):
                    base_trend = chart["trend_override"]
                elif chart.get("score", 5) >= 7:
                    base_trend = "strong_bullish"
                elif chart.get("score", 5) >= 6:
                    base_trend = "bullish"
                elif chart.get("score", 5) <= 3:
                    base_trend = "strong_bearish"
                elif chart.get("score", 5) <= 4:
                    base_trend = "bearish"
            except Exception:
                chart = {}

            upper_bb = chart.get("upper_bb", 0.0) or 0.0
            lower_bb = chart.get("lower_bb", 0.0) or 0.0

            # ── News + DB context (finvizfinance × MongoDB) ───────────────
            ticker_ctx: dict = {}
            db_note         = ""
            db_win_rate     = None
            try:
                from app.services.news_impact_analyzer import analyze_ticker_context
                ticker_ctx  = analyze_ticker_context(ticker, price)
                db_note     = ticker_ctx.get("note", "")
                db_win_rate = ticker_ctx.get("historical_win_rate")
                db_trend    = ticker_ctx.get("sentiment", "neutral")
                if db_trend != "neutral" and not skip_cooldown:
                    base_trend = db_trend
            except Exception:
                pass

            trend = base_trend

            # ── Build signal ──────────────────────────────────────────────
            signal = None
            if chart.get("is_sideways") and not skip_cooldown and iv_rank >= 30:
                signal = engine._build_iron_condor(
                    ticker, price, iv_rank, 35,
                    upper_bb=upper_bb, lower_bb=lower_bb,
                )
                adx_val = chart.get("adx", 0)
                rsi_bb  = chart.get("rsi", 0)
                signal.rationale = (
                    f"שוק דשדוש מובהק (ADX: {adx_val:.0f}, RSI: {rsi_bb:.0f}) — "
                    f"IC מותאם לרצועות בולינגר ({lower_bb:.1f}–{upper_bb:.1f})"
                )
                signal = engine._apply_margin(signal)
            else:
                signal = engine.select_strategy(
                    ticker=ticker, price=price, trend=trend,  # type: ignore[arg-type]
                    iv_rank=iv_rank, rsi=rsi_val, vix_level=vix,
                    has_earnings_soon=earnings, dte_preference=35,
                )

            if not signal:
                for try_trend in ["neutral", "bullish", "bearish", "strong_bullish", "strong_bearish"]:
                    if try_trend == trend:
                        continue
                    signal = engine.select_strategy(
                        ticker=ticker, price=price, trend=try_trend,  # type: ignore[arg-type]
                        iv_rank=iv_rank, rsi=rsi_val, vix_level=vix,
                        has_earnings_soon=earnings, dte_preference=35,
                    )
                    if signal:
                        break

            if not signal:
                if iv_rank >= 30:
                    signal = engine._build_iron_condor(
                        ticker, price, iv_rank, 35,
                        upper_bb=upper_bb, lower_bb=lower_bb,
                    )
                    signal.rationale = "ברירת מחדל — מניית מדד, IV בינוני"
                else:
                    signal = engine._build_bull_call_spread(ticker, price, iv_rank, 35)
                    signal.rationale = "IV נמוך — ספרד קנייה בדביט"
                signal = engine._apply_margin(signal)

            # ── Liquidity kill switch ─────────────────────────────────────
            if signal and signal.net_credit > 0:
                try:
                    from app.services.iv_calculator import get_real_option_data
                    liq = get_real_option_data(ticker, signal.dte, option_type="put")
                    if liq.get("volume", 0) < 10 or liq.get("open_interest", 0) < 50:
                        logger.info("strategies: %s killed — low liquidity", ticker)
                        continue
                except Exception:
                    pass

            if not signal:
                continue

            # ── Finviz context block ──────────────────────────────────────
            from app.services.finviz_service import get_stock_context, format_context_block
            fvz_ctx   = get_stock_context(ticker)
            fvz_block = format_context_block(fvz_ctx)

            toxic_warning = ""
            if fvz_ctx.get("massive_selling"):
                toxic_warning = (
                    "\u26a0\ufe0f *אזהרה קריטית:* "
                    "פנים מוכרים בכמות חריגה! "
                    "מכירת פרמיה על מניה זו מסוכנת במיוחד."
                )

            # Chart line
            chart_line = f"📊 {chart['summary']}" if chart.get("summary") else ""

            # Liquidity confirmation
            liq_line = ""
            try:
                from app.services.iv_calculator import get_real_option_data
                if signal.net_credit > 0:
                    liq = get_real_option_data(ticker, signal.dte, option_type="put")
                    liq_line = f"✅ נזילות: volume={liq.get('volume',0)}, OI={liq.get('open_interest',0)}"
            except Exception:
                pass

            # DB insight + news block
            ni_lines: list[str] = []
            if db_note:
                ni_lines.append(f"🤖 *DB Insight:* {db_note}")
            if db_win_rate is not None:
                wr_emoji = "🟢" if db_win_rate >= 55 else ("🔴" if db_win_rate < 40 else "🟡")
                ni_lines.append(f"{wr_emoji} Win Rate היסטורי: `{db_win_rate}%`")
            headlines = ticker_ctx.get("news_summary", [])
            if headlines:
                ni_lines.append(f"📰 *חדשות:* _{headlines[0][:100]}_")
            news_block = "\n".join(ni_lines)

            parts = [engine.format_telegram_message(signal)]
            if chart_line:
                parts.append(chart_line)
            if liq_line:
                parts.append(liq_line)
            if fvz_block:
                parts.append(fvz_block)
            if news_block:
                parts.append(news_block)
            if toxic_warning:
                parts.append(toxic_warning)

            signal.telegram_message = "\n\n".join(parts)
            messages.append(signal.telegram_message)

            # Persist
            try:
                if not skip_cooldown:
                    MongoDB.log_strategy_sent(ticker, signal.strategy_name, price)
                _log_ticker_for_training(ticker, price, signal.strategy_name)
            except Exception:
                pass

            logger.info(
                "[STRATEGIES] %s → %s | trend=%s | IV=%.0f | RSI=%.0f",
                ticker, signal.strategy_display, trend, iv_rank, rsi_val,
            )

        except Exception as e:
            logger.warning("strategies %s: %s", ticker, e)
            continue

    return messages


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


# ══════════════════════════════════════════════════════════════════════════════
# Script runner commands — every scan script is reachable from Telegram
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_daily_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run the full daily TA stock scan and send email report."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "📊 *סריקה יומית החלה...*\n"
        "מריץ ניתוח טכני על כל המועמדים.\n"
        "תקבל מייל כשהיא תסתיים.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await asyncio.to_thread(_sync_daily_scan)
        await update.message.reply_text("✅ *הסריקה היומית הושלמה!* בדוק את המייל שלך.", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_daily_scan failed")
        await update.message.reply_text(f"❌ הסריקה היומית נכשלה: {exc}")

def _sync_daily_scan():
    from run_daily_scan import run_scan
    run_scan()


async def cmd_options_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run the daily options brief (Finviz + XGBoost + SPX 0DTE + stock spreads)."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🎯 *סריקת אופציות החלה...*\n"
        "סורק את Finviz, מסנן עם XGBoost,\n"
        "בונה Iron Condor SPX + ספרדים על מניות.\n"
        "מייל בדרך.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await asyncio.to_thread(_sync_options_scan)
        await update.message.reply_text("✅ *דוח האופציות נשלח!* בדוק את המייל שלך.", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_options_scan failed")
        await update.message.reply_text(f"❌ סריקת אופציות נכשלה: {exc}")

def _sync_options_scan():
    from run_options_scan import run_options_scan
    run_options_scan()


async def cmd_smart_money(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run the Smart Money / Wyckoff institutional accumulation scanner."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🦅 *סריקת כסף חכם החלה...*\n"
        "מזהה דפוסי צבירה Wyckoff\n"
        "ופעילות מוסדית.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await asyncio.to_thread(_sync_smart_money)
        await update.message.reply_text("✅ *סריקת כסף חכם הושלמה!* בדוק את המייל שלך.", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_smart_money failed")
        await update.message.reply_text(f"❌ סריקת כסף חכם נכשלה: {exc}")

def _sync_smart_money():
    from run_smart_money import run_smart_money_tracker
    run_smart_money_tracker()


async def cmd_news_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show live market headlines via finvizfinance, then run full email scan."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("📰 *טוען חדשות שוק...*", parse_mode=ParseMode.MARKDOWN)
    try:
        # Show live headlines inline first (fast)
        headlines_msg = await asyncio.to_thread(_sync_get_live_news)
        await update.message.reply_text(headlines_msg, parse_mode="Markdown")
    except Exception as e:
        logger.debug("live news headlines failed: %s", e)

    # Then run the full email scan in background
    await update.message.reply_text("📧 מריץ סריקת חדשות מלאה — בדוק את המייל בסיום.")
    try:
        await asyncio.to_thread(_sync_news_scan)
        await update.message.reply_text("✅ *סריקת חדשות הושלמה!*", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_news_scan failed")
        await update.message.reply_text(f"❌ סריקת חדשות נכשלה: {exc}")


def _sync_get_live_news() -> str:
    """Fetch top market headlines via finvizfinance and return formatted message."""
    try:
        from finvizfinance.news import News
        fnews    = News()
        all_news = fnews.get_news()
        news_df  = all_news.get("news") if isinstance(all_news, dict) else all_news
        if news_df is None or (hasattr(news_df, "empty") and news_df.empty):
            return "⚠️ לא נמצאו חדשות כרגע."
        msg = "📰 *חדשות חמות מהשוק:*\n\n"
        for _, row in news_df.head(10).iterrows():
            title  = str(row.get("Title", "")).replace("\r\n", " ").strip()[:100]
            source = str(row.get("Source", ""))
            if title:
                msg += f"🔹 *{title}*\n   _{source}_\n\n"
        return msg or "⚠️ לא נמצאו חדשות."
    except Exception as e:
        return f"⚠️ לא ניתן לטעון חדשות: {e}"


def _sync_news_scan():
    from run_news_scan import run_hybrid_scan
    run_hybrid_scan(source="both")


async def cmd_market_intelligence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run market intelligence analysis (macro + sector rotation)."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🧠 *ניתוח מודיעין שוק החל...*\n"
        "מנתח הקשר מאקרו, רוטציית סקטורים\n"
        "ומיצוב מוסדי.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await asyncio.to_thread(_sync_market_intelligence)
        await update.message.reply_text("✅ *ניתוח מודיעין השוק הושלם!* בדוק את המייל שלך.", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_market_intelligence failed")
        await update.message.reply_text(f"❌ ניתוח מודיעין שוק נכשל: {exc}")

def _sync_market_intelligence():
    from run_market_intelligence import run_market_intelligence
    run_market_intelligence()


async def cmd_otc_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run the OTC penny stock scanner."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🔬 *סריקת OTC החלה...*\n"
        "סורק שוק ה-OTC לפעילות חריגה.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await asyncio.to_thread(_sync_otc_scan)
        await update.message.reply_text("✅ *סריקת OTC הושלמה!* בדוק את המייל שלך.", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_otc_scan failed")
        await update.message.reply_text(f"❌ סריקת OTC נכשלה: {exc}")

def _sync_otc_scan():
    from run_otc_scan import run_otc_pipeline
    run_otc_pipeline()


async def cmd_train_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrain the XGBoost ML model on the latest market data."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🤖 *אימון המודל החל...*\n"
        "התהליך עשוי לקחת מספר דקות.\n"
        "מאמן XGBoost על נתוני שוק עדכניים.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await asyncio.to_thread(_sync_train_model)
        await update.message.reply_text("✅ *אימון המודל הושלם!* המודל החדש פעיל.", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_train_model failed")
        await update.message.reply_text(f"❌ אימון המודל נכשל: {exc}")

def _sync_train_model():
    from train_model import train_xgb_model
    train_xgb_model()


# ── Restored simple command handlers (called by name-convention handlers) ─────

async def dailyscan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔍 מריץ סריקה יומית...")
    try:
        from app.services.openbb_service import get_finviz_with_openbb_fallback
        from app.services.ml_service import predict_confidence

        bullish, bearish = get_finviz_with_openbb_fallback(n=10)

        lines = ["📊 *סריקה יומית — תוצאות:*\n"]
        lines.append("📈 *שוריות:*")
        for t in bullish[:5]:
            conf = predict_confidence(t)
            conf_str = f"`{conf:.0f}%`" if conf else "N/A"
            lines.append(f"• {t} | ML: {conf_str}")

        lines.append("\n📉 *דוביות:*")
        for t in bearish[:3]:
            conf = predict_confidence(t)
            conf_str = f"`{conf:.0f}%`" if conf else "N/A"
            lines.append(f"• {t} | ML: {conf_str}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")

async def optionsscan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📊 מריץ סריקת אופציות...")
    try:
        from run_options_scan import run_options_scan
        run_options_scan()
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")

async def smartmoney_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🦅 מריץ Smart Money...")
    try:
        from run_smart_money import run_smart_money_tracker
        run_smart_money_tracker()
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📰 מחפש חדשות שוק...")
    try:
        from app.services.perplexity_service import PerplexityService
        from datetime import date
        svc = PerplexityService()
        if svc.is_available():
            today = date.today().strftime("%B %d, %Y")
            answer = svc.ask(
                f"Top 5 US stock market news today {today}. "
                f"Include: earnings, Fed news, sector moves. "
                f"Format as bullet points in Hebrew."
            )
            await update.message.reply_text(
                f"📰 *חדשות שוק — {today}*\n\n{answer}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "⚠️ Perplexity לא מוגדר. הוסף PERPLEXITY_API_KEY ל-Render."
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")

async def intelligence_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🧠 מריץ Market Intelligence...")
    try:
        from app.agent.market_regime_agent import MarketRegimeAgent
        agent = MarketRegimeAgent()
        report = agent.run()
        msg = report.summary_hebrew[:4000] if hasattr(report, "summary_hebrew") else "✅ Intelligence הושלם"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")

async def otc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔬 מריץ סריקת OTC...")
    try:
        from run_otc_scan import run_otc_pipeline
        run_otc_pipeline()
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")

async def train_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🤖 מאמן מחדש את מודל XGBoost...")
    try:
        from train_model import train_xgb_model
        train_xgb_model()
        await update.message.reply_text("✅ אימון הושלם!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def cmd_analyze_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /analyze TICKER — quick options-focused analysis: IV rank, best strategy, TA summary.
    For a full Goldman Sachs deep-dive email report, use /deepdive TICKER.
    """
    if not _is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "📌 שימוש: `/analyze טיקר`\nדוגמה: `/analyze AAPL`\n\n"
            "_לניתוח GS מלא + מייל: /deepdive AAPL_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    ticker = context.args[0].upper().strip()
    if not ticker.isalpha() or len(ticker) > 10:
        await update.message.reply_text(f"⚠️ Invalid ticker: `{ticker}`", parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(f"🔍 מנתח את *{ticker}*...", parse_mode=ParseMode.MARKDOWN)

    try:
        result = await asyncio.to_thread(_sync_analyze_ticker, ticker)
        try:
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(result)
    except Exception as exc:
        logger.exception("cmd_analyze_ticker failed for %s", ticker)
        await update.message.reply_text(f"❌ ניתוח {ticker} נכשל: {exc}")

def _sync_analyze_ticker(ticker: str) -> str:
    import yfinance as yf
    from app.services.options_strategy_engine import OptionsStrategyEngine
    from app.services.iv_calculator import (
        get_iv_rank, get_current_iv, get_vix_level,
        check_earnings_soon, get_nearest_expiry,
    )
    from app.services.ml_service import predict_confidence
    from app.services.xgb_filter import get_xgb_label

    engine   = OptionsStrategyEngine()
    stock    = yf.Ticker(ticker)
    price    = stock.fast_info.last_price
    if not price:
        return f"❌ לא ניתן לשלוף מחיר עבור *{ticker}*"

    iv_rank  = get_iv_rank(ticker)
    curr_iv  = get_current_iv(ticker)
    vix      = get_vix_level()
    earnings = check_earnings_soon(ticker, days=7)
    expiry   = get_nearest_expiry(ticker, 35)

    # XGBoost confidence
    xgb_conf  = predict_confidence(ticker)
    xgb_label = get_xgb_label(xgb_conf if xgb_conf is not None else 0.0)
    xgb_line  = f"`{xgb_conf:.1f}%` {xgb_label}" if xgb_conf is not None else "N/A"

    # Quick technicals + chart patterns from 3-month history
    chart_summary = ""
    try:
        from app.ta.chart_patterns import analyze_chart
        hist_df = stock.history(period="6mo")
        hist    = hist_df["Close"].dropna()
        sma50 = float(hist.rolling(50).mean().iloc[-1]) if len(hist) >= 50 else None
        delta = hist.diff()
        gain  = delta.clip(lower=0).rolling(14).mean().iloc[-1]
        loss  = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
        rsi   = round(100 - 100 / (1 + gain / max(loss, 1e-9)), 1) if len(hist) >= 14 else 50.0
        if sma50 and price > sma50 * 1.02:
            trend = "bullish"
        elif sma50 and price < sma50 * 0.98:
            trend = "bearish"
        else:
            trend = "neutral"
        chart = analyze_chart(ticker, hist_df)
        chart_summary = chart.get("summary", "")
        if chart["trend_override"]:
            trend = chart["trend_override"]
    except Exception:
        rsi, trend = 50.0, "neutral"

    # Find best strategy
    best = None
    for t in (trend, "neutral", "bullish", "bearish"):
        sig = engine.select_strategy(
            ticker=ticker, price=price, trend=t,  # type: ignore[arg-type]
            iv_rank=iv_rank, rsi=rsi, vix_level=vix,
            has_earnings_soon=earnings,
        )
        if sig:
            best = sig
            break

    iv_bar   = "🔥" * min(5, int(iv_rank / 20))
    rsi_tag  = "🟢 מכירת יתר" if rsi < 35 else ("🔴 קניית יתר" if rsi > 65 else "🟡 ניטרלי")
    header   = (
        f"📊 *{ticker}* — ניתוח מהיר\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💹 מחיר: `${price:.2f}`\n"
        f"🤖 XGBoost: {xgb_line}\n"
        f"📈 IV Rank: `{iv_rank:.0f}%` {iv_bar}\n"
        f"📊 IV נוכחי: `{curr_iv * 100:.1f}%`\n"
        f"📐 RSI(14): `{rsi:.1f}` — {rsi_tag}\n"
        f"📉 מגמה מול SMA50: `{trend.upper()}`\n"
        f"📅 פקיעה קרובה: `{expiry}`\n"
        f"⚠️ דוחות בקרוב: `{'כן' if earnings else 'לא'}`\n"
        f"🌡️ VIX: `{vix:.1f}`\n\n"
    )

    chart_block = f"\n{chart_summary}\n" if chart_summary else ""

    # ── FinViz fundamentals / news / insider ──────────────────────────────
    from app.services.finviz_service import get_stock_context, format_context_block
    fvz_ctx   = get_stock_context(ticker)
    fvz_block = format_context_block(fvz_ctx)
    fvz_section = f"\n{fvz_block}\n" if fvz_block else ""

    # Toxic warning: insider mass-selling
    toxic_warning = ""
    if fvz_ctx.get("massive_selling"):
        toxic_warning = (
            "\n\u26a0\ufe0f *אזהרה קריטית:* "
            "פנים מוכרים בכמות חריגה! "
            "מכירת פרמיה מסוכנת במיוחד עכשיו.\n"
        )

    if best:
        margin_line = ""
        if best.margin_required > 0:
            margin_line = (
                f"\n💼 *הון נדרש:* `${best.margin_required:.0f}` | "
                f"ROC: `{best.return_on_capital:.1f}%` {best.capital_efficiency}\n"
            )
        return (
            header
            + chart_block
            + fvz_section
            + toxic_warning
            + margin_line
            + engine.format_telegram_message(best)
        )

    iv_env = (
        "גבוה — שקול מכירת פרמיה" if iv_rank > 50
        else ("נמוך — שקול קניית אופציות" if iv_rank < 25 else "בינוני")
    )
    return (
        header
        + chart_block
        + fvz_section
        + toxic_warning
        + f"💡 סביבת IV: *{iv_env}*\n"
        + "⚠️ אין איתות אסטרטגיה ברור בתנאים הנוכחיים.\n"
        + "בדוק שוב כשה-IVR יעלה מעל 30 או יירד מתחת ל-25."
    )


# ══════════════════════════════════════════════════════════════════════════════
# /gex — Gamma Exposure conversational handler
# ══════════════════════════════════════════════════════════════════════════════

_GEX_TICKER_MAP = {
    "SPX": "SPY", "^SPX": "SPY", "^GSPC": "SPY",
    "NDX": "QQQ", "^NDX": "QQQ", "NQ": "QQQ",
    "RUT": "IWM", "^RUT": "IWM",
    "DJI": "DIA", "^DJI": "DIA",
    "VIX": "^VIX",
}


async def cmd_gex_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /gex — entry point. Asks user which ticker to analyze.
    Returns GEX_WAITING_TICKER state to wait for a reply.
    """
    if not _is_authorized(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "🎯 *ניתוח Gamma Exposure \\(GEX\\)*\n\n"
        "איזה טיקר תרצה לנתח?\n\n"
        "💡 *דוגמאות:*\n"
        "   SPY — מדד S&P 500\n"
        "   QQQ — מדד נאסד״ק\n"
        "   AAPL / NVDA / TSLA\n\n"
        "✍️ הקלד את שם הטיקר:",
        parse_mode="MarkdownV2",
    )
    return GEX_WAITING_TICKER


async def cmd_gex_receive_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Receives the ticker, runs GEX analysis, sends result.
    Returns ConversationHandler.END.
    """
    user_input = update.message.text.strip().upper()

    if not user_input or len(user_input) > 10 or not user_input.replace("^", "").isalpha():
        await update.message.reply_text(
            "⚠️ טיקר לא תקין. נסה שוב עם /gex\nדוגמאות: SPY, QQQ, AAPL, NVDA"
        )
        return ConversationHandler.END

    ticker = _GEX_TICKER_MAP.get(user_input, user_input)

    await update.message.reply_text(
        f"⏳ מחשב GEX עבור *{ticker}*...\n"
        f"_סורק את כל שרשרת האופציות עד 45 ימים — עשוי לקחת 30-60 שניות_",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        result_msg = await asyncio.to_thread(_run_gex_sync, ticker, 45)

        if len(result_msg) <= 4000:
            try:
                await update.message.reply_text(result_msg, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await update.message.reply_text(result_msg)
        else:
            # Split at the ASCII chart block
            chart_start = result_msg.find("```")
            if chart_start > 0:
                main_part  = result_msg[:chart_start].strip()
                chart_part = result_msg[chart_start:].strip()
                try:
                    await update.message.reply_text(main_part,  parse_mode=ParseMode.MARKDOWN)
                    await update.message.reply_text(chart_part, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await update.message.reply_text(main_part)
                    await update.message.reply_text(chart_part)
            else:
                await update.message.reply_text(result_msg[:3800])
                if len(result_msg) > 3800:
                    await update.message.reply_text(result_msg[3800:])

        await update.message.reply_text("🔄 רוצה לנתח טיקר נוסף? הקלד /gex שוב.")

    except Exception as e:
        logger.exception("cmd_gex_receive_ticker failed for %s", ticker)
        await update.message.reply_text(
            f"❌ שגיאה בניתוח {ticker}: {e}\nודא שהטיקר תקין ונסה שוב עם /gex"
        )

    return ConversationHandler.END


async def cmd_gex_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allow user to cancel mid-conversation with /cancel."""
    await update.message.reply_text("❌ ניתוח GEX בוטל.")
    return ConversationHandler.END


def _run_gex_sync(ticker: str, max_dte: int) -> str:
    """Synchronous wrapper for GEX calculation (runs in thread)."""
    from app.services.gex_analyzer import calculate_gex, format_gex_telegram
    result = calculate_gex(ticker, max_dte=max_dte)
    return format_gex_telegram(result)


async def gex_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show GEX analysis (SpotGamma methodology) + A/D Line: /gex [TICKER]"""
    if not _is_authorized(update):
        return

    symbol = context.args[0].upper() if context.args else "SPY"
    await update.message.reply_text(
        f"📊 מחשב GEX ל-*{symbol}*...\n"
        f"_סורק שרשרת אופציות + מחשב Zero Gamma, Call Wall, Put Wall (כ-30 שניות)_",
        parse_mode="Markdown",
    )

    try:
        from app.services.gex_calculator import calculate_gex, format_gex_hebrew
        from app.services.advance_decline import get_ad_line, format_ad_line_hebrew

        gex, ad = await asyncio.gather(
            asyncio.to_thread(lambda: calculate_gex(symbol)),
            asyncio.to_thread(get_ad_line),
        )

        if gex:
            msg = format_gex_hebrew(gex)
            try:
                await update.message.reply_text(msg, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"⚠️ לא הצלחתי לחשב GEX ל-{symbol}")

        if ad:
            msg = format_ad_line_hebrew(ad)
            try:
                await update.message.reply_text(msg, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(msg)

    except Exception as e:
        logger.exception("gex_command failed for %s", symbol)
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = """🤖 *HAI — סוכן מסחר AI אישי*
_מערכת Options Trading אוטונומית_

━━━━━━━━━━━━━━━━━━━━━━━━
🧠 *סוכנים ומצב מערכת*
• `/status` — מצב כל 3 הסוכנים + בריאות מערכת
• `/regime` — ניתוח Regime יומי (Bullish/Bearish/Neutral)
• `/strategist` — המלצות עסקאות לפי Regime + IV
• `/riskcheck` — ניהול סיכונים: P/L, Delta, exposure

━━━━━━━━━━━━━━━━━━━━━━━━
📊 *סריקות Options*
• `/scan TICKER` — Scanner מלא עם IV אמיתי (ברירת מחדל: SPY)
• `/scan NVDA` — ניתוח מלא ל-NVDA
• `/zerod` — 0DTE Analysis: SPX + SPY + QQQ
• `/zerod TICKER` — 0DTE על מניה ספציפית
• `/ivscan` — מניות עם IV Rank גבוה (הזדמנויות פרמיה)
• `/csp TICKER` — Cash Secured Put Scanner
• `/chainscreen TICKER` — Chain Screener: spread opportunities
• `/spxsignal` — SPX 0DTE Signal: entry/exit בזמן אמת

━━━━━━━━━━━━━━━━━━━━━━━━
📺 *TradingView Screener*
• `/tvscan strong_buy` — מניות Strong Buy בכל ה-timeframes
• `/tvscan oversold` — מניות Oversold (RSI<30)
• `/tvscan overbought` — מניות Overbought (RSI>70)
• `/tvscan breakout` — פריצות נפח גבוה
• `/tvscan momentum` — Momentum חזק

━━━━━━━━━━━━━━━━━━━━━━━━
🔬 *ניתוח מעמיק*
• `/deepscan TICKER` — ניתוח AI מלא: TA + IV + Sentiment + ML
• `/debate TICKER` — Bull vs Bear: 4 סוכנים מתווכחים
• `/earningstraddle` — Earnings Straddle Scanner (11 פילטרים)
• `/gex` — GEX Analysis + Gamma Levels + A/D Line
• `/gex TICKER` — GEX ספציפי למניה
• `/backtest TICKER STRATEGY` — Backtest היסטורי
• `/internet שאלה` — חיפוש Perplexity בזמן אמת

━━━━━━━━━━━━━━━━━━━━━━━━
💼 *פוזיציות*
• `/positions` — פוזיציות פתוחות + P/L
• `/addposition` — הוסף פוזיציה חדשה
• `/closeposition` — סגור פוזיציה

━━━━━━━━━━━━━━━━━━━━━━━━
🧠 *זיכרון ולמידה*
• `/myprofile` — הפרופיל שלי: watchlist, העדפות, אסטרטגיות
• `/memory` — 10 השיחות האחרונות
• `/summary` — סיכום שבועי: ביצועים + תובנות + דפוסים
• `/knowledge` — רשימת כל הידע שנלמד
• `/learn_url URL` — למד מקישור (אתר, YouTube, GitHub, X/Twitter, PDF)
• `/learn נושא | תוכן` — הוסף ידע ידני ישירות
• `/settings` — הגדרות הסוכן: שפה, אסטרטגיה, risk level
• `/reset` — נקה היסטוריית שיחה (הפרופיל נשמר)

━━━━━━━━━━━━━━━━━━━━━━━━
📰 *חדשות וניטור*
• `/monitor` — סריקה ידנית מיידית של כל הwatchlist
• `/briefing` — דוח בוקר: שוק + GEX + לוח אירועים
• `/watchlist` — הצג/ערוך את רשימת המעקב שלך
• `/watchlist add TICKER` — הוסף מניה למעקב
• `/alerts` — היסטוריית התראות אחרונות

━━━━━━━━━━━━━━━━━━━━━━━━
🤖 *ML / XGBoost*
• `/train` — אמן מחדש XGBoost (Fama-French features)
• `/leaderboard` — Top 15 מניות לפי XGBoost Score

━━━━━━━━━━━━━━━━━━━━━━━━
📎 *שלח ישירות — ללא פקודה:*
• 📷 תמונה/גרף → ניתוח Claude Vision (chart, options chain)
• 📄 PDF → קריאה ולמידה אוטומטית
• 💬 שאלה חופשית → תשובה עם זיכרון + context שוק

━━━━━━━━━━━━━━━━━━━━━━━━
🔔 *אוטומטי — בלי לבקש:*
🌅 `09:00` — דוח בוקר יומי בעברית
⚡ `כל 15 דקות` — תנועות >3%, IV spikes, Earnings warnings
🕷️ `כל 30 דקות` — SEC filings, Fed, Options flow חריג
🌙 `23:30` — סיכום יום + אירועי מחר"""

    await update.message.reply_text(msg, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/reset — Clear conversation history (profile is preserved)."""
    if not _is_authorized(update):
        return
    agent = get_agent()
    if agent.memory:
        agent.memory.clear_history()
    await update.message.reply_text(
        "🔄 היסטוריית השיחה נוקתה.\n"
        "הפרופיל שלך נשמר — אני עדיין זוכר מי אתה."
    )


async def learn_url_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/learn_url <URL> — Learn from any URL (webpage, YouTube, GitHub, X/Twitter, PDF)."""
    if not _is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text(
            "📝 שימוש: `/learn_url URL`\n\n"
            "עובד עם:\n"
            "• אתרים רגילים\n"
            "• YouTube\n"
            "• GitHub repos\n"
            "• X/Twitter threads\n"
            "• קישורי PDF",
            parse_mode="Markdown"
        )
        return

    url = context.args[0]
    await update.message.reply_text(f"📖 קורא ולומד מ: `{url}`...", parse_mode="Markdown")

    try:
        from app.services.learning_engine import LearningEngine
        result = await asyncio.to_thread(LearningEngine().learn_from_url, url)

        if result["success"]:
            try:
                await update.message.reply_text(
                    f"✅ *למדתי!*\n\n"
                    f"📌 נושא: `{result['topic']}`\n"
                    f"💾 נשמר: `{result['chars_saved']}` תווים\n\n"
                    f"📋 *תקציר:*\n{result['summary']}\n\n"
                    f"מעכשיו אשתמש במידע הזה בשיחות שלנו.",
                    parse_mode="Markdown"
                )
            except Exception:
                await update.message.reply_text(f"✅ למדתי! נושא: {result['topic']}")
        else:
            await update.message.reply_text(f"⚠️ שגיאה: {result['error']}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/learn [topic |] content — Learn from direct text input."""
    if not _is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text(
            "📝 שימוש: `/learn נושא | תוכן`\n\n"
            "דוגמה:\n"
            "`/learn Iron Condor | אסטרטגיה לשמירת פרמיה — מוכרים Call וPut OTM...`",
            parse_mode="Markdown"
        )
        return

    from datetime import datetime as _dt
    full_text = " ".join(context.args)
    if "|" in full_text:
        parts = full_text.split("|", 1)
        topic = parts[0].strip()
        content = parts[1].strip()
    else:
        topic = f"ידע {_dt.now().strftime('%d/%m %H:%M')}"
        content = full_text

    try:
        from app.services.learning_engine import LearningEngine
        result = await asyncio.to_thread(LearningEngine().learn_from_text, topic, content)

        if result["success"]:
            await update.message.reply_text(
                f"✅ שמרתי!\n📌 נושא: `{topic}`\n💾 {result['chars_saved']} תווים",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"⚠️ שגיאה: {result['error']}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def knowledge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/knowledge — List all learned knowledge."""
    if not _is_authorized(update):
        return
    try:
        from app.services.learning_engine import LearningEngine
        knowledge = LearningEngine().list_knowledge()

        if not knowledge:
            await update.message.reply_text(
                "📭 עדיין לא למדתי שום דבר חדש.\n"
                "שלח `/learn_url URL` כדי שאלמד מקישור."
            )
            return

        lines = [f"🧠 *הידע שצברתי ({len(knowledge)} נושאים):*\n"]
        for i, k in enumerate(knowledge[:15], 1):
            topic = k.get("topic", "")
            ts = k.get("updated_at", k.get("learned_at", ""))
            ts_str = ts.strftime("%d/%m") if hasattr(ts, "strftime") else str(ts)[:10]
            lines.append(f"{i}. `{topic}` — {ts_str}")

        try:
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("\n".join(lines))

    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photos — analyze with Claude Vision and save insights."""
    if not _is_authorized(update):
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    caption = update.message.caption or ""

    import io
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    try:
        from app.services.learning_engine import LearningEngine
        result = await asyncio.to_thread(
            LearningEngine().learn_from_image, image_bytes, "image/jpeg", caption
        )

        if result["success"]:
            saved_note = "\n\n✅ *נשמר לזיכרון*" if result.get("saved_to_memory") else ""
            try:
                await update.message.reply_text(
                    f"🖼️ *ניתוח תמונה:*\n\n{result['analysis']}{saved_note}",
                    parse_mode="Markdown"
                )
            except Exception:
                await update.message.reply_text(result["analysis"])
        else:
            await update.message.reply_text(f"⚠️ שגיאה בניתוח: {result['error']}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle documents (PDF, TXT) — extract and learn."""
    if not _is_authorized(update):
        return
    doc = update.message.document
    if not doc:
        return

    await update.message.reply_text(
        f"📄 קורא את הקובץ: `{doc.file_name}`...", parse_mode="Markdown"
    )

    try:
        import io
        file = await context.bot.get_file(doc.file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        file_bytes = buf.getvalue()

        from app.services.learning_engine import LearningEngine
        engine = LearningEngine()

        if doc.mime_type == "application/pdf" or (doc.file_name or "").endswith(".pdf"):
            result = await asyncio.to_thread(
                engine.learn_from_pdf_bytes, file_bytes, doc.file_name or "PDF"
            )
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
            result = await asyncio.to_thread(
                engine.learn_from_text, doc.file_name or "Document", text
            )

        if result["success"]:
            try:
                await update.message.reply_text(
                    f"✅ *למדתי מהקובץ!*\n\n"
                    f"📌 נושא: `{result['topic']}`\n"
                    f"💾 נשמר: `{result['chars_saved']}` תווים\n\n"
                    f"📋 *תקציר:*\n{result.get('summary', '')[:400]}\n\n"
                    f"מעכשיו אשתמש במידע הזה בשיחות.",
                    parse_mode="Markdown"
                )
            except Exception:
                await update.message.reply_text(
                    f"✅ למדתי מהקובץ: {result['topic']}"
                )
        else:
            await update.message.reply_text(f"⚠️ שגיאה: {result['error']}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def myprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/myprofile — Show user profile."""
    if not _is_authorized(update):
        return
    agent = get_agent()
    if not agent.memory:
        await update.message.reply_text("⚠️ זיכרון לא זמין")
        return
    profile = agent.memory.get_profile()
    watchlist = ", ".join(profile.get("watchlist", []))
    strategies = ", ".join(profile.get("favorite_strategies", profile.get("strategies", [])))
    knowledge = agent.memory.list_knowledge()
    knowledge_list = "\n".join(f"  • {k['topic']}" for k in knowledge[:5]) or "  אין עדיין"
    msg = (
        f"👤 *הפרופיל שלי — חיים*\n"
        f"{'━'*28}\n\n"
        f"📈 *מניות במעקב:*\n{watchlist}\n\n"
        f"🎯 *אסטרטגיות מועדפות:*\n{strategies}\n\n"
        f"🧠 *ידע שנלמד:*\n{knowledge_list}\n\n"
        f"🏦 ברוקר: {profile.get('broker', 'IB Israel')}\n"
        f"🎯 מטרה: {profile.get('goal', '$1,000/שבוע')}"
    )
    try:
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(msg)


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/memory — Show recent conversation history."""
    if not _is_authorized(update):
        return
    agent = get_agent()
    if not agent.memory:
        await update.message.reply_text("⚠️ זיכרון לא זמין")
        return
    messages = agent.memory.get_recent_messages(limit=5)
    if not messages:
        await update.message.reply_text("📭 אין היסטוריית שיחות עדיין.")
        return
    lines = ["🧠 *5 ההודעות האחרונות:*\n"]
    for m in messages:
        role = "אתה" if m["role"] == "user" else "🤖"
        content = m["content"][:80] + "..." if len(m["content"]) > 80 else m["content"]
        lines.append(f"*{role}:* {content}")
    try:
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("\n".join(lines))


async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /leaderboard
    Ranks all tickers seen in the last 48 h by XGBoost confidence.
    Shows top 15 candidates with score + label.
    """
    if not _is_authorized(update):
        return

    await update.message.reply_text("🏆 טוען טבלת דירוג ML...")

    try:
        result = await asyncio.to_thread(_run_leaderboard_sync)
        try:
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(result)
    except Exception as exc:
        logger.exception("cmd_leaderboard failed")
        await update.message.reply_text(f"❌ שגיאה בטבלת דירוג: {exc}")


def _run_leaderboard_sync() -> str:
    from app.data.mongo_client import MongoDB
    from app.services.xgb_filter import enrich_with_confidence, get_xgb_label

    candidates = MongoDB.get_recent_scanner_candidates(hours=48)
    if not candidates:
        return "⚠️ לא נמצאו מועמדים מסריקות אחרונות.\nהרץ /dailyscan או /optionsscan תחילה."

    ranked = enrich_with_confidence(candidates)
    top    = ranked[:15]

    lines = [
        f"🏆 *טבלת דירוג ML — XGBoost*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"מדורג לפי: הסתברות לעלייה ≥5% ב-10 ימים\n"
        f"גודל מאגר: {len(candidates)} מניות\n"
    ]
    for i, (conf, ticker) in enumerate(top, start=1):
        label = get_xgb_label(conf)
        score = f"`{conf:.1f}%`" if conf > 0 else "`N/A`"
        lines.append(f"{i:>2}. `{ticker:<6}` {score} {label}")

    return "\n".join(lines)


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
# /regime — Agent 1: Market Regime Analyst
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_regime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/regime — Run Agent 1 (Market Regime Analyst) on demand."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("🧠 מריץ את Agent 1 — Market Regime Analyst...")
    try:
        from app.agent.market_regime_agent import MarketRegimeAgent
        report = await asyncio.to_thread(lambda: MarketRegimeAgent().run())
        try:
            await update.message.reply_text(report.summary_hebrew, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(report.summary_hebrew)
    except Exception as e:
        logger.exception("cmd_regime failed")
        await update.message.reply_text(f"❌ שגיאה בניתוח משטר שוק: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# /strategist — Agent 2: Options Strategist
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_strategist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/strategist — Run Agent 2 (Options Strategist) on demand."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("👨‍💼 מריץ את Agent 2 — Options Strategist...")
    try:
        from app.agent.options_strategist_agent import OptionsStrategistAgent
        report = await asyncio.to_thread(lambda: OptionsStrategistAgent().run())
        msg = report.summary_hebrew[:4000]
        try:
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(msg)
    except Exception as e:
        logger.exception("cmd_strategist failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Options Engine — /scan command
# ══════════════════════════════════════════════════════════════════════════════

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/scan [TICKER ...] — Run options engine scanner."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("🔍 סורק אופציות... ~30 שניות")
    try:
        from app.options_engine.scanner import run_options_engine
        symbols = [a.upper() for a in context.args] if context.args else None
        results = run_options_engine(symbols)
        if not results:
            await update.message.reply_text("😴 לא נמצאו הזדמנויות. נסה כשהשוק פתוח.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 0DTE Scanner — /zerod command
# ══════════════════════════════════════════════════════════════════════════════

async def zerod_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """0DTE analysis and setup recommendation."""
    if not _is_authorized(update):
        return
    symbols = [a.upper() for a in context.args] if context.args else ["SPY", "QQQ"]
    await update.message.reply_text(f"📅 מנתח 0DTE עבור {', '.join(symbols)}...")
    try:
        from app.services.zero_dte_scanner import analyze_zero_dte, format_zero_dte_report
        for sym in symbols[:3]:
            setup = analyze_zero_dte(sym)
            msg = format_zero_dte_report(setup)
            await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Agent 3 Commands — Position tracking & risk management
# ══════════════════════════════════════════════════════════════════════════════

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/positions — Show all open positions."""
    if not _is_authorized(update):
        return
    from app.agent.risk_manager_agent import RiskManagerAgent
    summary = RiskManagerAgent.get_open_positions_summary()
    try:
        await update.message.reply_text(summary, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(summary)


async def addposition_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addposition — Add a new open position.
    Usage: /addposition TICKER STRATEGY SHORT_STRIKE LONG_STRIKE CREDIT EXPIRATION [CONTRACTS]
    Example: /addposition AAPL BullPutSpread 175 170 1.65 2026-05-16 2
    """
    if not _is_authorized(update):
        return
    try:
        args = context.args
        if not args or len(args) < 6:
            await update.message.reply_text(
                "📝 *שימוש:*\n"
                "`/addposition TICKER STRATEGY SHORT_STRIKE LONG_STRIKE CREDIT EXPIRATION [CONTRACTS]`\n\n"
                "*דוגמה:*\n"
                "`/addposition AAPL BullPutSpread 175 170 1.65 2026-05-16 2`\n\n"
                "STRATEGY: BullPutSpread | BearCallSpread | IronCondor",
                parse_mode="Markdown",
            )
            return

        ticker       = args[0].upper()
        strategy     = (args[1]
                        .replace("BullPutSpread", "Bull Put Spread")
                        .replace("BearCallSpread", "Bear Call Spread")
                        .replace("IronCondor", "Iron Condor"))
        short_strike = float(args[2])
        long_strike  = float(args[3])
        credit       = float(args[4])
        expiration   = args[5]  # YYYY-MM-DD
        contracts    = int(args[6]) if len(args) > 6 else 1
        spread_width = abs(short_strike - long_strike)

        from app.agent.risk_manager_agent import RiskManagerAgent
        ok = RiskManagerAgent.add_position(
            ticker=ticker,
            strategy=strategy,
            short_strike=short_strike,
            long_strike=long_strike,
            credit_received=credit,
            spread_width=spread_width,
            expiration_date=expiration,
            contracts=contracts,
        )

        if ok:
            max_loss = round((spread_width - credit) * 100 * contracts, 2)
            await update.message.reply_text(
                f"✅ *פוזיציה נוספה!*\n\n"
                f"📌 {ticker} — {strategy}\n"
                f"💰 Credit: `${credit}` | Spread: `${spread_width}`\n"
                f"📅 פקיעה: `{expiration}`\n"
                f"📦 חוזים: `{contracts}`\n"
                f"⚠️ Max Loss: `${max_loss}`\n\n"
                f"🤖 Agent 3 יתחיל לעקוב מהשעה הבאה.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("⚠️ שגיאה בהוספת הפוזיציה.")

    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"⚠️ שגיאה בפרמטרים: {e}\nבדוק את הפורמט.")


async def closeposition_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /closeposition — Mark a position as closed.
    Usage: /closeposition TICKER CLOSE_PRICE
    Example: /closeposition AAPL 0.82
    """
    if not _is_authorized(update):
        return
    try:
        args = context.args
        if not args or len(args) < 2:
            await update.message.reply_text(
                "📝 *שימוש:*\n"
                "`/closeposition TICKER CLOSE_PRICE`\n\n"
                "*דוגמה:*\n"
                "`/closeposition AAPL 0.82`",
                parse_mode="Markdown",
            )
            return

        ticker      = args[0].upper()
        close_price = float(args[1])

        from app.agent.risk_manager_agent import RiskManagerAgent
        ok = RiskManagerAgent.close_position(ticker, close_price)

        if ok:
            await update.message.reply_text(
                f"✅ *פוזיציה נסגרה!*\n\n"
                f"📌 {ticker} סומנה כסגורה במחיר `${close_price}`\n"
                f"Agent 3 הפסיק לעקוב.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"⚠️ לא נמצאה פוזיציה פתוחה ל-{ticker}.")

    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def riskcheck_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/riskcheck — Manually trigger Agent 3 risk check right now."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("🕵️ מריץ בדיקת סיכונים על כל הפוזיציות...")
    try:
        from app.agent.risk_manager_agent import RiskManagerAgent
        result = await asyncio.to_thread(lambda: RiskManagerAgent().run())
        await update.message.reply_text(
            f"✅ בדיקה הושלמה.\n"
            f"📋 פוזיציות שנבדקו: `{result['checked']}`\n"
            f"🔔 התראות שנשלחו: `{result['alerts_sent']}`"
        )
    except Exception as e:
        logger.exception("riskcheck_command failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show health status of all 3 agents."""
    try:
        from app.agent.orchestrator import AgentOrchestrator
        o = AgentOrchestrator()
        status_msg = o.get_status()
        await update.message.reply_text(status_msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה בשליפת סטטוס: {e}")


async def chainscreen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/chainscreen TICKER — Screen full options chain for best Bull Put Spread + BWB."""
    if not _is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text(
            "📝 שימוש: `/chainscreen TICKER`\nדוגמה: `/chainscreen AAPL`",
            parse_mode="Markdown",
        )
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"🔍 סורק options chain של {ticker}... (עד 30 שניות)")
    try:
        from app.services.options_chain_screener import (
            find_best_credit_spread, find_broken_wing_butterfly, format_credit_spread_hebrew,
        )
        spread, bwb = await asyncio.gather(
            asyncio.to_thread(lambda: find_best_credit_spread(ticker)),
            asyncio.to_thread(lambda: find_broken_wing_butterfly(ticker)),
        )
        if not spread and not bwb:
            await update.message.reply_text(
                f"⚠️ לא נמצאה הזדמנות ב-{ticker}.\n"
                "נסה מניה אחרת עם IV Rank גבוה יותר, או בדוק שיש אופציות נזילות."
            )
            return
        lines = [f"🎯 *Chain Screen — {ticker}*\n"]
        if spread:
            lines.append(format_credit_spread_hebrew(spread))
        if bwb:
            lines.append("\n" + format_credit_spread_hebrew(bwb))
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.exception("chainscreen_command failed for %s", ticker)
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def spxsignal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/spxsignal — SPX 0DTE straddle signal: buy or sell based on actual vs expected move."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("📊 מחשב SPX 0DTE Signal...")
    try:
        from app.services.ibkr_service import get_spx_0dte_signal
        sig = await asyncio.to_thread(get_spx_0dte_signal)
        action = {
            "buy_straddle": "📈 קנה Straddle",
            "sell_condor":  "📉 מכור Iron Condor",
            "neutral":      "➡️ ניטרלי",
        }.get(sig["signal"], "⚪")
        msg = (
            f"📊 *SPX 0DTE Signal*\n{'━' * 26}\n\n"
            f"🎯 *{action}*\n\n"
            f"📐 תנועה ממוצעת: `${sig.get('mean_actual', 0)}`\n"
            f"📐 תנועה צפויה: `${sig.get('expected', 0)}`\n"
            f"📊 יחס: `{sig.get('ratio', 1):.2f}x`\n\n"
            f"💡 {sig.get('reason', '')}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.exception("spxsignal_command failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def ivscan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ivscan [TICKERS] [--min-rank N] — Scan for high IV stocks and explain why."""
    if not _is_authorized(update):
        return

    args = context.args or []
    custom_tickers = [a.upper() for a in args if not a.startswith("--")] or None
    min_rank = 50.0
    for i, a in enumerate(args):
        if a == "--min-rank" and i + 1 < len(args):
            try:
                min_rank = float(args[i + 1])
            except ValueError:
                pass

    await update.message.reply_text("🔍 סורק IV גבוה... (עד 45 שניות)")

    try:
        from app.services.iv_scanner import scan_high_iv, format_iv_scan_telegram, fetch_x_mentions

        results = await asyncio.to_thread(
            lambda: scan_high_iv(tickers=custom_tickers, min_iv_rank=min_rank, max_results=8)
        )

        perplexity_notes = {}
        if results:
            top_tickers = [r.ticker for r in results[:5]]
            perplexity_notes = await asyncio.to_thread(fetch_x_mentions, top_tickers)

        msg = format_iv_scan_telegram(results, perplexity_notes)
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("ivscan_command failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def backtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run Bull Put Spread backtest via backtest_engine.py."""
    if not _is_authorized(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📝 שימוש: `/backtest TICKER`\nדוגמה: `/backtest AAPL`",
            parse_mode="Markdown",
        )
        return

    ticker = args[0].upper()
    await update.message.reply_text(f"📊 מריץ Backtest על {ticker}... (כ-20 שניות)")

    try:
        from app.services.backtest_engine import (
            backtest_bull_put_spread,
            format_backtest_hebrew,
        )
        result = await asyncio.to_thread(lambda: backtest_bull_put_spread(ticker))
        if result:
            msg = format_backtest_hebrew(result)
            try:
                await update.message.reply_text(msg, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(msg)
        else:
            await update.message.reply_text(
                f"⚠️ לא הצלחתי להריץ backtest על {ticker}.\n"
                f"ייתכן שאין מספיק היסטוריה או אופציות זמינות."
            )
    except Exception as e:
        logger.exception("backtest_command failed for %s", ticker)
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def tvscan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scan stocks by TradingView signal type: /tvscan oversold"""
    if not _is_authorized(update):
        return

    valid_signals = ["oversold", "overbought", "trending_up", "trending_down", "breakout", "strong_buy"]
    signal = context.args[0].lower() if context.args else "oversold"

    if signal not in valid_signals:
        await update.message.reply_text(
            f"📝 סיגנלים זמינים: {', '.join(valid_signals)}\n"
            f"דוגמה: `/tvscan oversold`",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(f"🔍 סורק מניות עם סיגנל: *{signal}*...", parse_mode="Markdown")

    try:
        from app.services.tradingview_service import scan_by_signal_type
        results = await asyncio.to_thread(
            lambda: scan_by_signal_type(signal=signal, exchange="NASDAQ")
        )
        if not results:
            await update.message.reply_text("⚠️ לא נמצאו תוצאות — ייתכן שהמודול לא מותקן")
            return

        lines = [f"📊 *TradingView Scan — {signal.upper()}*\n"]
        for r in results[:8]:
            ticker = r.get("symbol", "")
            rec = r.get("recommendation", "")
            price = r.get("price", 0)
            change = r.get("change_percent", 0)
            emoji = "📈" if change >= 0 else "📉"
            lines.append(f"• *{ticker}* | ${price:.2f} {emoji}{change:+.1f}% | {rec}")

        try:
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.exception("tvscan_command failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def debate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run Bull vs Bear debate on a ticker: /debate AAPL"""
    if not _is_authorized(update):
        return

    ticker = context.args[0].upper() if context.args else ""
    if not ticker:
        await update.message.reply_text(
            "📝 שימוש: `/debate AAPL`\n\n"
            "מריץ דיון Bull vs Bear — 4 סוכנים מנתחים את המניה:\n"
            "🐂 Bull Researcher → 🐻 Bear Researcher → ⚖️ Judge → 🛡️ Risk Manager\n\n"
            "הדיון מבוסס על: IV Rank, מחיר, RSI, TA Score, חדשות Perplexity, Regime",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"⚔️ מתחיל Bull vs Bear Debate על *{ticker}*...\n"
        f"4 סוכנים עובדים בסדרה (~25 שניות)",
        parse_mode="Markdown",
    )
    try:
        from app.services.bull_bear_debate import run_bull_bear_debate, format_debate_hebrew
        result = await asyncio.to_thread(lambda: run_bull_bear_debate(ticker))
        msg = format_debate_hebrew(result)
        for chunk in _split_message_bot(msg):
            try:
                await update.message.reply_text(chunk, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(chunk)
    except Exception as e:
        logger.exception("debate_command failed for %s", ticker)
        await update.message.reply_text(f"⚠️ שגיאה בדיון: {e}")


async def earningstraddle_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Scan for Earnings Straddle opportunities."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🎯 סורק Earnings Straddle...\n"
        "מחפש מניות עם Earnings בעוד 3 ימים שעוברות את כל הסינונים\n"
        "(כ-30 שניות)"
    )
    try:
        from app.services.earnings_straddle_scanner import (
            scan_earnings_straddle,
            format_earnings_straddle_hebrew,
        )
        results = await asyncio.to_thread(
            lambda: scan_earnings_straddle(days_ahead=3, max_results=5)
        )
        msg = format_earnings_straddle_hebrew(results)
        for chunk in _split_message_bot(msg):
            try:
                await update.message.reply_text(chunk, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(chunk)
    except Exception as e:
        logger.exception("earningstraddle_command failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def internet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Direct internet search via Perplexity."""
    if not _is_authorized(update):
        return

    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "📝 שימוש: `/internet <שאלה>`\n\n"
            "דוגמאות:\n"
            "• `/internet why is NVDA up today`\n"
            "• `/internet what sectors are hot this week`\n"
            "• `/internet AAPL latest earnings results`\n"
            "• `/internet next big AI trend`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(f"🌐 מחפש באינטרנט: _{query}_...", parse_mode="Markdown")

    try:
        from app.services.perplexity_service import PerplexityService
        svc = PerplexityService()
        if not svc.is_available():
            await update.message.reply_text(
                "⚠️ Perplexity לא מוגדר.\n"
                "הוסף PERPLEXITY_API_KEY ב-Render Environment Variables."
            )
            return

        result = await asyncio.to_thread(svc.search, query, 1000)
        if result:
            await update.message.reply_text(
                f"🌐 *תוצאה מהאינטרנט:*\n\n{result}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ לא נמצאה תשובה.")
    except Exception as e:
        logger.exception("internet_command failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def csp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scan for Cash Secured Put opportunities."""
    if not _is_authorized(update):
        return

    args = context.args or []

    # Parse: /csp [max_price] [tickers...]
    max_price = 20.0
    custom_tickers = None

    if args:
        try:
            max_price = float(args[0])
            custom_tickers = [a.upper() for a in args[1:]] or None
        except ValueError:
            custom_tickers = [a.upper() for a in args]

    await update.message.reply_text(
        f"🔍 סורק CSP — מניות עד ${max_price:.0f}...\n"
        f"(בודק פרמיות, נזילות, מגמה — כ-30 שניות)"
    )

    try:
        from app.services.csp_scanner import scan_csp_opportunities, format_csp_hebrew
        results = await asyncio.to_thread(
            lambda: scan_csp_opportunities(
                max_price=max_price,
                custom_tickers=custom_tickers,
                max_results=6,
            )
        )
        msg = format_csp_hebrew(results)
        try:
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(msg)
    except Exception as e:
        logger.exception("csp_command failed")
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def deepscan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/deepscan [TICKER ...] — Deep smart scan: fundamentals + momentum + AI insight + trend themes."""
    if not _is_authorized(update):
        return

    args = [a.upper() for a in context.args] if context.args else []
    tickers = args[:3]  # max 3 tickers

    if tickers:
        await update.message.reply_text(
            f"🔬 מריץ Deep Scan על {', '.join(tickers)}... (עד 60 שניות)",
        )
        try:
            from app.services.smart_scanner import deep_scan_ticker, format_smart_scan_hebrew
            for ticker in tickers:
                result = await asyncio.to_thread(
                    lambda t=ticker: deep_scan_ticker(t, fetch_perplexity=True)
                )
                if result:
                    msg = format_smart_scan_hebrew(result)
                    for chunk in _split_message_bot(msg):
                        try:
                            await update.message.reply_text(chunk, parse_mode="Markdown")
                        except Exception:
                            await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(f"⚠️ לא הצלחתי לסרוק את {ticker}")
        except Exception as e:
            logger.exception("deepscan_command failed for %s", tickers)
            await update.message.reply_text(f"⚠️ שגיאה: {e}")

    else:
        await update.message.reply_text(
            "🌊 מריץ Deep Scan על טרנדים חמים... (עד 90 שניות)",
        )
        try:
            from app.services.smart_scanner import scan_trending_themes, format_smart_scan_hebrew
            results = await asyncio.to_thread(lambda: scan_trending_themes(top_n=3))
            if not results:
                await update.message.reply_text("⚠️ לא נמצאו הזדמנויות בסריקת טרנדים כרגע.")
                return
            for r in results:
                msg = format_smart_scan_hebrew(r)
                for chunk in _split_message_bot(msg):
                    try:
                        await update.message.reply_text(chunk, parse_mode="Markdown")
                    except Exception:
                        await update.message.reply_text(chunk)
        except Exception as e:
            logger.exception("deepscan_command (themes) failed")
            await update.message.reply_text(f"⚠️ שגיאה בסריקת טרנדים: {e}")


def _split_message_bot(text: str, limit: int = 4000) -> list[str]:
    """Split long messages for Telegram (4096 char limit)."""
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


async def evaluate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/evaluate TICKER — Evaluate if a Bull Put Spread setup is worth taking right now."""
    if not _is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text(
            "📝 שימוש: `/evaluate TICKER`\nדוגמה: `/evaluate AAPL`",
            parse_mode="Markdown",
        )
        return

    ticker = context.args[0].upper()
    await update.message.reply_text(f"🔍 מעריך עסקה על {ticker}...")

    try:
        from app.services.realtime_market_data import get_realtime_iv_data
        from app.services.technical_indicators import get_technical_snapshot
        from app.services.pcr_signal import get_pcr_signal
        from app.services.iv_calculator import check_earnings_soon, get_vix_level
        from app.services.trade_rules import evaluate_bull_put_entry, format_signal_hebrew

        iv_data, tech, pcr, vix, has_earnings = await asyncio.gather(
            asyncio.to_thread(lambda: get_realtime_iv_data(ticker)),
            asyncio.to_thread(lambda: get_technical_snapshot(ticker)),
            asyncio.to_thread(lambda: get_pcr_signal("SPY")),
            asyncio.to_thread(get_vix_level),
            asyncio.to_thread(lambda: check_earnings_soon(ticker, days=14)),
        )

        signal = evaluate_bull_put_entry(
            ticker=ticker,
            price=iv_data.current_price,
            iv_rank=iv_data.iv_rank,
            rsi=tech.rsi_14 if tech else 50.0,
            macd_histogram=tech.macd_histogram if tech else 0.0,
            adx=tech.adx if tech else 20.0,
            trend=tech.trend_signal if tech else "neutral",
            dte=38,
            vix=vix,
            pcr=pcr.pcr if pcr else 1.0,
        )

        msg = format_signal_hebrew(signal, ticker)
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("evaluate_command failed for %s", ticker)
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage news alert watchlist: /watchlist show|add TICKER|remove TICKER|scan|clear"""
    if not _is_authorized(update):
        return

    from app.services.news_alert_engine import (
        _get_watchlist, add_to_watchlist, remove_from_watchlist,
        reset_watchlist, run_news_scan_job,
    )

    args = context.args or []
    subcmd = args[0].lower() if args else "show"

    if subcmd == "show" or not args:
        wl = _get_watchlist()
        tickers_str = " · ".join(f"`{t}`" for t in wl)
        await update.message.reply_text(
            f"📋 *Watchlist — {len(wl)} מניות*\n\n{tickers_str}\n\n"
            f"פקודות:\n"
            f"• `/watchlist add NVDA` — הוסף\n"
            f"• `/watchlist remove NVDA` — הסר\n"
            f"• `/watchlist scan` — סרוק עכשיו\n"
            f"• `/watchlist clear` — אפס לברירת מחדל",
            parse_mode="Markdown",
        )

    elif subcmd == "add":
        if len(args) < 2:
            await update.message.reply_text("⚠️ נא לציין טיקר: `/watchlist add NVDA`", parse_mode="Markdown")
            return
        ticker = args[1].upper()
        wl = add_to_watchlist(ticker)
        await update.message.reply_text(
            f"✅ `{ticker}` נוסף ל-Watchlist.\nסה\"כ: {len(wl)} מניות.",
            parse_mode="Markdown",
        )

    elif subcmd == "remove":
        if len(args) < 2:
            await update.message.reply_text("⚠️ נא לציין טיקר: `/watchlist remove NVDA`", parse_mode="Markdown")
            return
        ticker = args[1].upper()
        wl = remove_from_watchlist(ticker)
        await update.message.reply_text(
            f"🗑️ `{ticker}` הוסר מה-Watchlist.\nנשארו: {len(wl)} מניות.",
            parse_mode="Markdown",
        )

    elif subcmd == "clear":
        wl = reset_watchlist()
        await update.message.reply_text(
            f"♻️ Watchlist אופס לברירת מחדל — {len(wl)} מניות.",
        )

    elif subcmd == "scan":
        await update.message.reply_text("🔍 סורק חדשות לכל ה-Watchlist... (עד 2 דקות)")
        try:
            alerts = await run_news_scan_job()
            if alerts:
                await update.message.reply_text(
                    f"✅ הסריקה הושלמה — {len(alerts)} התראות נשלחו."
                )
            else:
                await update.message.reply_text("✅ הסריקה הושלמה — אין קטליסטים חמים כרגע.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ שגיאה בסריקה: {e}")

    else:
        await update.message.reply_text(
            "⚠️ פקודה לא מוכרת.\nאפשרויות: `show` | `add TICKER` | `remove TICKER` | `scan` | `clear`",
            parse_mode="Markdown",
        )


async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show last 10 news alerts from MongoDB: /alerts"""
    if not _is_authorized(update):
        return

    await update.message.reply_text("📋 טוען התראות אחרונות...")

    try:
        from app.data.mongo_client import MongoDB
        db = await asyncio.to_thread(MongoDB.get_db)
        docs = list(
            db["news_alerts_log"]
            .find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(10)
        )

        if not docs:
            await update.message.reply_text("📭 אין התראות קודמות ב-7 הימים האחרונים.")
            return

        lines = [f"📋 *{len(docs)} התראות אחרונות*\n{'━'*28}"]
        for doc in docs:
            ts = doc.get("timestamp")
            ts_str = ts.strftime("%m/%d %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
            magnitude_emoji = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(doc.get("magnitude", ""), "📰")
            lines.append(
                f"\n{magnitude_emoji} *{doc.get('ticker')}* — _{ts_str}_\n"
                f"  Catalyst: `{doc.get('catalyst_type', 'N/A')}` | Score: `{doc.get('catalyst_score', 0)}`\n"
                f"  {doc.get('headline', '')[:80]}"
            )

        try:
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("\n".join(lines))

    except Exception as e:
        logger.exception("alerts_command failed")
        await update.message.reply_text(f"⚠️ שגיאה בטעינת התראות: {e}")


# ══════════════════════════════════════════════════════════════════════════════
async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/monitor — Manual trigger for live monitor 15min scan."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("🔍 מריץ סריקה ידנית עכשיו...")
    try:
        from app.services.live_monitor import run_15min_scan
        await run_15min_scan()
        await update.message.reply_text("✅ סריקה הושלמה. אם יש התראות — נשלחו.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/briefing — Manual morning briefing."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("🌅 מכין דוח בוקר...")
    try:
        from app.services.live_monitor import send_morning_briefing
        await send_morning_briefing()
    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/settings — Manage agent preferences."""
    if not _is_authorized(update):
        return

    from app.services.memory_engine import MemoryEngine
    mem = MemoryEngine()
    args = context.args or []

    if not args or args[0].lower() == "show":
        profile = mem.get_profile()
        msg = (
            f"⚙️ *הגדרות נוכחיות:*\n\n"
            f"• רמת סיכון: `{profile.get('risk_tolerance', 'moderate')}`\n"
            f"• DTE מועדף: `{profile.get('preferred_dte', '30-45')}`\n"
            f"• מטרה: {profile.get('goal', 'לא הוגדר')}\n"
            f"• ברוקר: {profile.get('broker', 'IB Israel')}\n"
            f"• מניות במעקב: {', '.join(profile.get('watchlist', []))}\n\n"
            f"פקודות:\n"
            f"• `/settings risk low/moderate/aggressive`\n"
            f"• `/settings dte 30`\n"
            f"• `/settings goal טקסט`"
        )
        try:
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(msg)
        return

    action = args[0].lower()

    if action == "risk" and len(args) > 1:
        risk = args[1].lower()
        if risk in ("low", "moderate", "aggressive"):
            mem.update_profile({"risk_tolerance": risk})
            await update.message.reply_text(f"✅ רמת סיכון עודכנה: `{risk}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ השתמש: low / moderate / aggressive")

    elif action == "dte" and len(args) > 1:
        mem.update_profile({"preferred_dte": args[1]})
        await update.message.reply_text(f"✅ DTE מועדף: `{args[1]}`", parse_mode="Markdown")

    elif action == "goal" and len(args) > 1:
        goal = " ".join(args[1:])
        mem.update_profile({"goal": goal})
        await update.message.reply_text(f"✅ מטרה עודכנה: {goal}")

    else:
        await update.message.reply_text("⚠️ פקודה לא מוכרת. שלח `/settings` לעזרה.")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/summary — Generate weekly conversation summary and insights."""
    if not _is_authorized(update):
        return
    await update.message.reply_text("📊 מכין סיכום שבועי...")

    try:
        from app.services.memory_engine import MemoryEngine
        import anthropic as _anthropic

        mem = MemoryEngine()
        messages = mem.get_recent_messages(limit=50)

        if not messages:
            await update.message.reply_text("📭 אין היסטוריית שיחות עדיין.")
            return

        conversation_text = "\n".join([
            f"{m['role'].upper()}: {m['content'][:200]}"
            for m in messages[-30:]
        ])

        client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": (
                    f"סכם את השיחות האחרונות הבאות בין חיים לסוכן:\n\n"
                    f"{conversation_text}\n\n"
                    f"כתוב סיכום בעברית הכולל:\n"
                    f"1. מניות שנדונו\n"
                    f"2. אסטרטגיות שנדונו\n"
                    f"3. שאלות חוזרות\n"
                    f"4. תובנות חשובות\n"
                    f"5. מה כדאי לעקוב אחריו"
                )
            }]
        )

        summary = response.content[0].text.strip()
        insights = mem.get_conversation_insights()
        knowledge = mem.list_knowledge()

        msg = (
            f"📊 *סיכום שבועי*\n"
            f"{'━'*28}\n\n"
            f"{summary}\n\n"
            f"{'━'*28}\n"
            f"🧠 *ידע שנצבר:* {len(knowledge)} נושאים\n"
            f"💬 *שיחות:* {len(messages)} הודעות\n\n"
            f"📌 *דפוסים שזיהיתי:*\n{insights}"
        )
        try:
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"⚠️ שגיאה: {e}")


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

    # ── GEX — SpotGamma methodology (replaces old conversation handler) ──────
    app.add_handler(CommandHandler("gex", gex_command))

    # ── Core ──────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("help",         help_command))
    app.add_handler(CommandHandler("status",       status_command))
    app.add_handler(CommandHandler("market",       cmd_status))
    app.add_handler(CommandHandler("options",      cmd_options_0dte))
    app.add_handler(CommandHandler("scan",         scan_command))
    app.add_handler(CommandHandler("newscan",      cmd_scan))

    # ── Deep dive GS research note + email (was /analyze) ────────────────────
    app.add_handler(CommandHandler("deepdive",     cmd_analyze))

    # ── Options strategy (quick + deep) ──────────────────────────────────────
    app.add_handler(CommandHandler("analyze",      cmd_analyze_ticker))
    app.add_handler(CommandHandler("strategies",   cmd_strategies))
    app.add_handler(CommandHandler("quick_scan",   cmd_quick_scan))
    app.add_handler(CommandHandler("trade_check",  cmd_trade_check))

    # ── Scan runners ─────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("dailyscan",    dailyscan_command))
    app.add_handler(CommandHandler("optionsscan",  optionsscan_command))
    app.add_handler(CommandHandler("smartmoney",   smartmoney_command))
    app.add_handler(CommandHandler("news",         news_command))
    app.add_handler(CommandHandler("intelligence", intelligence_command))
    app.add_handler(CommandHandler("otc",          otc_command))
    app.add_handler(CommandHandler("train",        train_command))
    app.add_handler(CommandHandler("leaderboard",  cmd_leaderboard))
    app.add_handler(CommandHandler("regime",        cmd_regime))
    app.add_handler(CommandHandler("strategist",   cmd_strategist))
    app.add_handler(CommandHandler("zerod",        zerod_command))

    # ── Agent 3 — Position tracking & risk management ─────────────────────────
    app.add_handler(CommandHandler("positions",    positions_command))
    app.add_handler(CommandHandler("addposition",  addposition_command))
    app.add_handler(CommandHandler("closeposition", closeposition_command))
    app.add_handler(CommandHandler("riskcheck",    riskcheck_command))

    # ── High IV Scanner ───────────────────────────────────────────────────────
    app.add_handler(CommandHandler("ivscan",       ivscan_command))

    # ── Options Chain Screener + SPX Signal ───────────────────────────────────
    app.add_handler(CommandHandler("chainscreen",  chainscreen_command))
    app.add_handler(CommandHandler("spxsignal",    spxsignal_command))

    # ── Backtest + Trade evaluation ────────────────────────────────────────────
    app.add_handler(CommandHandler("backtest",     backtest_command))
    app.add_handler(CommandHandler("evaluate",     evaluate_command))

    # ── Deep Smart Scanner ────────────────────────────────────────────────────
    app.add_handler(CommandHandler("deepscan",     deepscan_command))

    # ── Cash Secured Put Scanner ──────────────────────────────────────────────
    app.add_handler(CommandHandler("csp",          csp_command))

    # ── Internet search (Perplexity) ──────────────────────────────────────────
    app.add_handler(CommandHandler("internet",     internet_command))

    # ── Earnings Straddle Scanner ─────────────────────────────────────────────
    app.add_handler(CommandHandler("earningstraddle", earningstraddle_command))

    # ── Bull vs Bear Debate ───────────────────────────────────────────────────
    app.add_handler(CommandHandler("debate",          debate_command))

    # ── TradingView Scanner ───────────────────────────────────────────────────
    app.add_handler(CommandHandler("tvscan",          tvscan_command))

    # ── News Alert System ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("watchlist",       watchlist_command))
    app.add_handler(CommandHandler("alerts",          alerts_command))

    # ── Memory & learning commands ────────────────────────────────────────────
    app.add_handler(CommandHandler("reset",           reset_command))
    app.add_handler(CommandHandler("learn",           learn_command))
    app.add_handler(CommandHandler("learn_url",       learn_url_command))
    app.add_handler(CommandHandler("knowledge",       knowledge_command))
    app.add_handler(CommandHandler("myprofile",       myprofile_command))
    app.add_handler(CommandHandler("memory",          memory_command))

    # ── Live monitor (manual triggers) ────────────────────────────────────────
    app.add_handler(CommandHandler("monitor",         monitor_command))
    app.add_handler(CommandHandler("briefing",        briefing_command))

    # ── Agent preferences & summary ───────────────────────────────────────────
    app.add_handler(CommandHandler("settings",        settings_command))
    app.add_handler(CommandHandler("summary",         summary_command))

    # ── Free chat — MUST be registered LAST so it doesn't shadow /commands ────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
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
