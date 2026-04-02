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

    Run the multi-strategy options engine. Without args: scans fresh Finviz tickers.
    With args: analyze specific tickers only (max 10).
    """
    if not _is_authorized(update):
        return

    args = list(context.args) if context.args else []
    await update.message.reply_text("⏳ מריץ מנוע אסטרטגיות אופציות...")

    try:
        messages = await asyncio.to_thread(_run_strategies_sync, args)
        if not messages:
            await update.message.reply_text("⚠️ לא נמצאו אותות אסטרטגיה בתנאי השוק הנוכחיים.")
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
    Fixed:
    - Fetches Finviz + TradingView tickers (not inside loop)
    - Assigns correct trend per ticker
    - Handles SPX/index tickers correctly (^GSPC, ^SPX → SPY)
    - Falls back gracefully when IV rank unavailable
    - Tries multiple trend values to find a signal
    """
    import yfinance as yf
    from app.services.options_strategy_engine import OptionsStrategyEngine
    from app.services.iv_calculator import get_iv_rank, get_vix_level, check_earnings_soon
    from app.services.finviz_service import FinvizService
    from app.data.mongo_client import MongoDB

    engine   = OptionsStrategyEngine()
    vix      = get_vix_level()
    messages = []
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

    # ── Build ticker list ─────────────────────────────────────────────────
    if args:
        raw = [normalize(t) for t in args[:10]]
        tickers_with_trend = [(t, "neutral") for t in raw]
        skip_cooldown = True
    else:
        # Fetch from Finviz ONCE — before any loop
        bull_tickers: list[str] = []
        bear_tickers: list[str] = []
        tv_tickers:   list[str] = []

        try:
            bull_tickers = FinvizService.get_bullish_tickers(n=12) or []
        except Exception as e:
            logger.warning("Finviz bullish failed: %s", e)

        try:
            bear_tickers = FinvizService.get_bearish_tickers(n=6) or []
        except Exception as e:
            logger.warning("Finviz bearish failed: %s", e)

        # Also try TradingView if available
        try:
            from app.services.tradingview_service import TradingViewService
            tv_raw = TradingViewService.get_candidates_from_url(
                "https://www.tradingview.com/screener/BmHEGvNM/"
            ) or []
            tv_tickers = [normalize(t) for t in tv_raw[:8]]
        except Exception:
            tv_tickers = []

        seen: set[str] = set()
        tickers_with_trend: list[tuple[str, str]] = []

        for t in bull_tickers:
            t = normalize(t)
            if t not in seen:
                tickers_with_trend.append((t, "bullish"))
                seen.add(t)

        for t in bear_tickers:
            t = normalize(t)
            if t not in seen:
                tickers_with_trend.append((t, "bearish"))
                seen.add(t)

        for t in tv_tickers:
            if t not in seen:
                tickers_with_trend.append((t, "neutral"))
                seen.add(t)

        skip_cooldown = False

    # ── Fallback: if Finviz returned nothing, use default watchlist ───────
    if not tickers_with_trend:
        DEFAULT_WATCHLIST: list[tuple[str, str]] = [
            ("SPY", "neutral"), ("QQQ", "neutral"), ("AAPL", "bullish"),
            ("NVDA", "bullish"), ("TSLA", "neutral"), ("AMD", "bullish"),
            ("MSFT", "bullish"), ("META", "bullish"), ("AMZN", "bullish"),
        ]
        tickers_with_trend = DEFAULT_WATCHLIST
        logger.warning("[STRATEGIES] Finviz returned nothing — using default watchlist")

    # ── Process each ticker ───────────────────────────────────────────────
    for ticker, base_trend in tickers_with_trend[:15]:

        # Cooldown check
        if not skip_cooldown:
            try:
                if MongoDB.was_strategy_sent_recently(ticker, days=COOLDOWN_DAYS):
                    logger.info("strategies: %s in cooldown — skipping", ticker)
                    continue
            except Exception:
                pass

        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if not price or price <= 0:
                continue

            # Get IV rank — default to 50 if unavailable (medium)
            try:
                iv_rank = get_iv_rank(ticker)
            except Exception:
                iv_rank = 50.0

            # Get earnings
            try:
                earnings = check_earnings_soon(ticker, days=7)
            except Exception:
                earnings = False

            # Calculate RSI from price history
            rsi_val = 50.0
            try:
                hist = stock.history(period="1mo")
                if len(hist) >= 14:
                    delta = hist["Close"].diff()
                    gain  = delta.clip(lower=0).rolling(14).mean()
                    loss  = (-delta.clip(upper=0)).rolling(14).mean()
                    rs    = gain / loss
                    rsi_s = 100 - (100 / (1 + rs))
                    rsi_val = float(rsi_s.iloc[-1])
            except Exception:
                pass

            # ── Try to find a signal — attempt multiple trend values ──────
            signal = None
            trend  = base_trend

            # First try the Finviz-derived trend (with chart pattern override)
            try:
                from app.ta.chart_patterns import analyze_chart
                chart = analyze_chart(ticker, stock.history(period="3mo"))
                if chart.get("trend_override") and not skip_cooldown:
                    trend = chart["trend_override"]
            except Exception:
                chart = {}

            signal = engine.select_strategy(
                ticker=ticker, price=price, trend=trend,  # type: ignore[arg-type]
                iv_rank=iv_rank, rsi=rsi_val, vix_level=vix,
                has_earnings_soon=earnings, dte_preference=35,
            )

            # If no signal, try trend fallbacks
            if not signal:
                trend_fallbacks = ["neutral", "bullish", "bearish",
                                   "strong_bullish", "strong_bearish"]
                for try_trend in trend_fallbacks:
                    if try_trend == trend:
                        continue
                    signal = engine.select_strategy(
                        ticker=ticker, price=price, trend=try_trend,  # type: ignore[arg-type]
                        iv_rank=iv_rank, rsi=rsi_val, vix_level=vix,
                        has_earnings_soon=earnings, dte_preference=35,
                    )
                    if signal:
                        break

            # Last resort: force a strategy based on IV level
            if not signal:
                if iv_rank >= 30:
                    signal = engine._build_iron_condor(ticker, price, iv_rank, 35)
                    signal.rationale = "איתות ברירת מחדל — IV בינוני, שוק ניטרלי"
                else:
                    signal = engine._build_bull_call_spread(ticker, price, iv_rank, 35)
                    signal.rationale = "IV נמוך — ספרד קנייה בדביט"

            if signal:
                # ── Per-ticker context: news + chart + liquidity ──────────
                context_lines = []

                # 1. Recent news headline
                try:
                    from app.services.news_scraper import NewsScraper
                    scraper  = NewsScraper()
                    raw_news = scraper.get_stock_news(ticker, limit=3)
                    if raw_news:
                        top = raw_news[0].get("headline", "")[:100]
                        context_lines.append(f"📰 חדשות: _{top}_")
                except Exception:
                    pass

                # 2. Chart pattern summary
                try:
                    chart_hist = stock.history(period="3mo")
                    if not chart_hist.empty and len(chart_hist) >= 20:
                        from app.ta.chart_patterns import analyze_chart
                        chart_info = analyze_chart(ticker, chart_hist)
                        if chart_info.get("summary"):
                            context_lines.append(f"📊 {chart_info['summary']}")
                        if chart_info.get("patterns"):
                            context_lines.append(f"   תבנית: {chart_info['patterns'][0]}")
                except Exception:
                    pass

                # 3. Liquidity check on real option data
                try:
                    from app.services.iv_calculator import get_real_option_data
                    if signal.net_credit > 0:
                        liq = get_real_option_data(ticker, signal.dte, option_type="put")
                        vol = liq.get("volume", 0)
                        oi  = liq.get("open_interest", 0)
                        if vol < 10 or oi < 100:
                            context_lines.append(f"⚠️ נזילות נמוכה: volume={vol}, OI={oi}")
                        else:
                            context_lines.append(f"✅ נזילות: volume={vol}, OI={oi}")
                except Exception:
                    pass

                context_block = "\n".join(context_lines)
                signal.telegram_message = (
                    engine.format_telegram_message(signal)
                    + (f"\n\n{context_block}" if context_block else "")
                )
                messages.append(signal.telegram_message)

                # Save to MongoDB + training
                try:
                    if not skip_cooldown:
                        MongoDB.log_strategy_sent(ticker, signal.strategy_name, price)
                    _log_ticker_for_training(ticker, price, signal.strategy_name)
                except Exception:
                    pass

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
    """Run the news scanner and send alerts for significant headlines."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "📰 *סריקת חדשות החלה...*\n"
        "סורק כותרות אחרונות שמניעות את השוק.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await asyncio.to_thread(_sync_news_scan)
        await update.message.reply_text("✅ *סריקת חדשות הושלמה!*", parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("cmd_news_scan failed")
        await update.message.reply_text(f"❌ סריקת חדשות נכשלה: {exc}")

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

    if best:
        return header + chart_block + engine.format_telegram_message(best)

    iv_env = (
        "גבוה — שקול מכירת פרמיה" if iv_rank > 50
        else ("נמוך — שקול קניית אופציות" if iv_rank < 25 else "בינוני")
    )
    return (
        header
        + chart_block
        + f"💡 סביבת IV: *{iv_env}*\n"
        + "⚠️ אין איתות אסטרטגיה ברור בתנאים הנוכחיים.\n"
        + "בדוק שוב כשה-IVR יעלה מעל 30 או יירד מתחת ל-25."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all available bot commands."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🤖 *בוט stocks-finder — כל הפקודות*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 *סריקות (שולחות דוח במייל):*\n"
        "/dailyscan — סריקה יומית מלאה עם ניתוח טכני\n"
        "/optionsscan — דוח אופציות יומי (SPX + מניות)\n"
        "/smartmoney — זיהוי צבירה מוסדית (Wyckoff)\n"
        "/news — סריקת חדשות שוק אחרונות\n"
        "/intelligence — ניתוח מאקרו + רוטציית סקטורים\n"
        "/otc — סורק מניות OTC\n\n"
        "🎯 *אסטרטגיות אופציות:*\n"
        "/strategies — סריקת מניות Finviz לאסטרטגיה האופטימלית\n"
        "/strategies AAPL TSLA — ניתוח מניות ספציפיות\n"
        "/analyze טיקר — ניתוח מעמיק: IV + אסטרטגיה + ML\n"
        "/trade\\_check טיקר — המלצת Wheel/Spread מפורטת\n"
        "/quick\\_scan — רשימה קומפקטית: מניה | אסטרטגיה | סיכוי | הכנסה\n\n"
        "🔬 *מחקר:*\n"
        "/deepdive טיקר — ניתוח עמוק + דוח במייל\n\n"
        "🤖 *מודל ML:*\n"
        "/train — אימון מחדש של מודל XGBoost\n"
        "/leaderboard — Top 15 מניות לפי ציון ML (48 שעות אחרונות)\n\n"
        "ℹ️ *מערכת:*\n"
        "/status — סנפשוט שוק (VIX + מאקרו)\n"
        "/options — הגדרת Iron Condor 0DTE על SPX\n"
        "/help — ההודעה הזו\n\n"
        "📅 *תזמון אוטומטי:* סריקה יומית ב-16:45 שעון ישראל, ראשון–חמישי",
        parse_mode=ParseMode.MARKDOWN,
    )


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
# Bot setup + run
# ══════════════════════════════════════════════════════════════════════════════

def build_app() -> Application:
    """Build and return the configured Telegram Application."""
    global _app
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = Application.builder().token(token).build()
    # ── Core ──────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CommandHandler("status",       cmd_status))
    app.add_handler(CommandHandler("options",      cmd_options_0dte))
    app.add_handler(CommandHandler("scan",         cmd_scan))

    # ── Deep dive GS research note + email (was /analyze) ────────────────────
    app.add_handler(CommandHandler("deepdive",     cmd_analyze))

    # ── Options strategy (quick + deep) ──────────────────────────────────────
    app.add_handler(CommandHandler("analyze",      cmd_analyze_ticker))
    app.add_handler(CommandHandler("strategies",   cmd_strategies))
    app.add_handler(CommandHandler("quick_scan",   cmd_quick_scan))
    app.add_handler(CommandHandler("trade_check",  cmd_trade_check))

    # ── Scan runners ─────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("dailyscan",    cmd_daily_scan))
    app.add_handler(CommandHandler("optionsscan",  cmd_options_scan))
    app.add_handler(CommandHandler("smartmoney",   cmd_smart_money))
    app.add_handler(CommandHandler("news",         cmd_news_scan))
    app.add_handler(CommandHandler("intelligence", cmd_market_intelligence))
    app.add_handler(CommandHandler("otc",          cmd_otc_scan))
    app.add_handler(CommandHandler("train",        cmd_train_model))
    app.add_handler(CommandHandler("leaderboard",  cmd_leaderboard))
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
