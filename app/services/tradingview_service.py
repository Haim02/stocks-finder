"""
tradingview_service.py — TradingView Intelligence Layer
=======================================================

Wraps tradingview-mcp-server tools for use across the entire agent system.

Provides to EVERY command and free chat:
- Real-time prices (no API key needed)
- 30+ technical indicators
- 15 candlestick patterns
- Multi-timeframe analysis (Weekly→Daily→4H→1H)
- Market snapshot (SPY, VIX, BTC, EUR/USD)
- Reddit sentiment
- Backtesting (6 strategies + Sharpe/Calmar/Win Rate)
- Stock screener by signal type

Source: atilaahmettaner/tradingview-mcp (2.1K stars, Python, MIT)
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Cache to avoid duplicate calls
_cache: dict = {}
_CACHE_TTL = 600  # 10 minutes


def _cached(key: str, ttl: int = _CACHE_TTL):
    """Simple TTL cache — returns (get_fn, set_fn) pair."""
    def get():
        entry = _cache.get(key)
        if entry:
            data, ts = entry
            if time.time() - ts < ttl:
                return data
        return None

    def set_(data):
        _cache[key] = (data, time.time())

    return get, set_


_tv_warned = False  # log missing-package warning only once

def _import_tv():
    """Lazy import of tradingview_mcp tools. Returns None if not installed."""
    global _tv_warned
    try:
        from tradingview_mcp import (
            get_technical_analysis,
            get_bollinger_band_analysis,
            get_candlestick_patterns,
            get_multi_timeframe_analysis,
            get_stock_decision,
            market_snapshot,
            yahoo_price,
            market_sentiment,
            backtest_strategy,
            compare_strategies,
            scan_by_signal,
            screen_stocks,
        )
        return {
            "get_technical_analysis": get_technical_analysis,
            "get_bollinger_band_analysis": get_bollinger_band_analysis,
            "get_candlestick_patterns": get_candlestick_patterns,
            "get_multi_timeframe_analysis": get_multi_timeframe_analysis,
            "get_stock_decision": get_stock_decision,
            "market_snapshot": market_snapshot,
            "yahoo_price": yahoo_price,
            "market_sentiment": market_sentiment,
            "backtest_strategy": backtest_strategy,
            "compare_strategies": compare_strategies,
            "scan_by_signal": scan_by_signal,
            "screen_stocks": screen_stocks,
        }
    except ImportError:
        if not _tv_warned:
            logger.warning(
                "tradingview-mcp-server not installed — run: pip install tradingview-mcp-server"
            )
            globals()["_tv_warned"] = True
        return None
    except Exception as e:
        logger.warning("tradingview-mcp import failed: %s", e)
        return None


# ── Core data functions ───────────────────────────────────────────────────────

def get_tv_technical(ticker: str, exchange: str = "NASDAQ") -> Optional[dict]:
    """
    Full technical analysis from TradingView.
    Returns RSI, MACD, Bollinger, 23 indicators with BUY/SELL/HOLD signals.
    No API key required.
    """
    cache_get, cache_set = _cached(f"tv_tech_{ticker}")
    cached = cache_get()
    if cached is not None:
        return cached

    tv = _import_tv()
    if not tv:
        return None

    try:
        result = tv["get_technical_analysis"](
            symbol=ticker,
            exchange=exchange,
            interval="1d",
        )
        cache_set(result)
        return result
    except Exception as e:
        logger.debug("TV technical failed for %s: %s", ticker, e)
        return None


def get_tv_candlestick_patterns(ticker: str) -> Optional[dict]:
    """
    Detect 15 candlestick patterns: Doji, Hammer, Engulfing, etc.
    Used to confirm entry signals.
    """
    cache_get, cache_set = _cached(f"tv_candle_{ticker}", ttl=300)
    cached = cache_get()
    if cached is not None:
        return cached

    tv = _import_tv()
    if not tv:
        return None

    try:
        result = tv["get_candlestick_patterns"](symbol=ticker)
        cache_set(result)
        return result
    except Exception as e:
        logger.debug("TV candlestick failed for %s: %s", ticker, e)
        return None


def get_tv_multi_timeframe(ticker: str) -> Optional[dict]:
    """
    Multi-timeframe analysis: Weekly→Daily→4H→1H→15m alignment.
    All timeframes agree = strong signal.
    """
    cache_get, cache_set = _cached(f"tv_mtf_{ticker}", ttl=900)
    cached = cache_get()
    if cached is not None:
        return cached

    tv = _import_tv()
    if not tv:
        return None

    try:
        result = tv["get_multi_timeframe_analysis"](symbol=ticker)
        cache_set(result)
        return result
    except Exception as e:
        logger.debug("TV multi-timeframe failed for %s: %s", ticker, e)
        return None


def get_tv_decision(ticker: str) -> Optional[dict]:
    """
    3-layer decision engine from TradingView.
    Returns: STRONG BUY / BUY / HOLD / SELL / STRONG SELL + confidence.
    """
    cache_get, cache_set = _cached(f"tv_decision_{ticker}", ttl=600)
    cached = cache_get()
    if cached is not None:
        return cached

    tv = _import_tv()
    if not tv:
        return None

    try:
        result = tv["get_stock_decision"](symbol=ticker)
        cache_set(result)
        return result
    except Exception as e:
        logger.debug("TV decision failed for %s: %s", ticker, e)
        return None


def get_market_snapshot() -> Optional[dict]:
    """
    Global market snapshot: S&P500, NASDAQ, VIX, BTC, ETH, EUR/USD, SPY, GLD.
    Used by Agent 1 for Regime detection and free chat.
    """
    cache_get, cache_set = _cached("tv_snapshot", ttl=300)
    cached = cache_get()
    if cached is not None:
        return cached

    tv = _import_tv()
    if not tv:
        return None

    try:
        result = tv["market_snapshot"]()
        cache_set(result)
        return result
    except Exception as e:
        logger.debug("TV market snapshot failed: %s", e)
        return None


def get_reddit_sentiment(ticker: str) -> Optional[dict]:
    """
    Reddit sentiment: wallstreetbets, stocks, investing, options.
    Returns: bullish/bearish score + top posts.
    """
    cache_get, cache_set = _cached(f"tv_reddit_{ticker}", ttl=1800)
    cached = cache_get()
    if cached is not None:
        return cached

    tv = _import_tv()
    if not tv:
        return None

    try:
        result = tv["market_sentiment"](symbol=ticker)
        cache_set(result)
        return result
    except Exception as e:
        logger.debug("TV reddit sentiment failed for %s: %s", ticker, e)
        return None


def run_backtest(
    ticker: str,
    strategy: str = "rsi",
    period: str = "1y",
) -> Optional[dict]:
    """
    Backtest a strategy: rsi, bollinger, macd, ema_cross, supertrend, donchian.
    Returns: Win Rate, Return%, Sharpe, Calmar, Max Drawdown, vs Buy&Hold.
    """
    tv = _import_tv()
    if not tv:
        return None

    try:
        return tv["backtest_strategy"](
            symbol=ticker,
            strategy=strategy,
            period=period,
        )
    except Exception as e:
        logger.debug("TV backtest failed for %s/%s: %s", ticker, strategy, e)
        return None


def compare_all_strategies(ticker: str, period: str = "1y") -> Optional[dict]:
    """
    Run ALL 6 strategies and rank by performance.
    Best for /backtest command.
    """
    tv = _import_tv()
    if not tv:
        return None

    try:
        return tv["compare_strategies"](symbol=ticker, period=period)
    except Exception as e:
        logger.debug("TV compare strategies failed for %s: %s", ticker, e)
        return None


def scan_by_signal_type(
    signal: str = "oversold",
    exchange: str = "NASDAQ",
) -> Optional[list]:
    """
    Scan stocks by signal: oversold, overbought, trending_up, trending_down, breakout, strong_buy.
    Used to find candidates for CSP, Bull Put, 0DTE.
    """
    cache_get, cache_set = _cached(f"tv_scan_{signal}_{exchange}", ttl=600)
    cached = cache_get()
    if cached is not None:
        return cached

    tv = _import_tv()
    if not tv:
        return None

    try:
        result = tv["scan_by_signal"](signal=signal, exchange=exchange)
        cache_set(result)
        return result
    except Exception as e:
        logger.debug("TV scan by signal failed: %s", e)
        return None


# ── Formatting functions ──────────────────────────────────────────────────────

def format_tv_technical_hebrew(ticker: str, data: dict) -> str:
    """Format TradingView technical analysis for Telegram."""
    if not data:
        return ""

    recommendation = data.get("recommendation", "NEUTRAL")
    rec_label = {
        "STRONG_BUY": "🚀 STRONG BUY",
        "BUY": "🟢 BUY",
        "NEUTRAL": "➡️ NEUTRAL",
        "SELL": "🔴 SELL",
        "STRONG_SELL": "🔴🔴 STRONG SELL",
    }.get(recommendation, recommendation)

    oscillators = data.get("oscillators", {})
    moving_avgs = data.get("moving_averages", {})

    lines = [f"[TradingView Analysis — {ticker}]", f"המלצה: {rec_label}"]

    if oscillators:
        lines.append(
            f"Oscillators: 🟢{oscillators.get('BUY', 0)} Buy | "
            f"🔴{oscillators.get('SELL', 0)} Sell | "
            f"➡️{oscillators.get('NEUTRAL', 0)} Neutral"
        )
    if moving_avgs:
        lines.append(
            f"Moving Averages: 🟢{moving_avgs.get('BUY', 0)} Buy | "
            f"🔴{moving_avgs.get('SELL', 0)} Sell"
        )

    return "\n".join(lines)


def format_candlestick_hebrew(ticker: str, data: dict) -> str:
    """Format candlestick patterns for Telegram."""
    if not data:
        return ""

    patterns = data.get("patterns", [])
    if not patterns:
        return ""

    lines = [f"[Candlestick Patterns — {ticker}]"]
    for p in patterns[:5]:
        name = p.get("pattern", "")
        direction = p.get("direction", "")
        emoji = "🟢" if direction == "bullish" else "🔴" if direction == "bearish" else "⚪"
        lines.append(f"  {emoji} {name} ({direction})")

    return "\n".join(lines)


def format_multi_timeframe_hebrew(ticker: str, data: dict) -> str:
    """Format multi-timeframe analysis for Telegram."""
    if not data:
        return ""

    timeframes = {"1W": "שבועי", "1D": "יומי", "4h": "4 שעות", "1h": "שעתי", "15m": "15 דקות"}
    lines = [f"[Multi-Timeframe — {ticker}]"]
    buy_count = sell_count = 0

    for tf_key, tf_name in timeframes.items():
        tf_data = data.get(tf_key, {})
        if tf_data:
            rec = tf_data.get("recommendation", "NEUTRAL")
            emoji = "🟢" if "BUY" in rec else "🔴" if "SELL" in rec else "➡️"
            lines.append(f"  {emoji} {tf_name}: {rec}")
            if "BUY" in rec:
                buy_count += 1
            elif "SELL" in rec:
                sell_count += 1

    if buy_count >= 4:
        lines.append("✅ יישור שורי חזק — רוב הטיימפריימים מסכימים")
    elif sell_count >= 4:
        lines.append("⚠️ יישור דובי חזק — רוב הטיימפריימים מסכימים")
    else:
        lines.append("⚠️ אותות מעורבים — אין יישור ברור בין הטיימפריימים")

    return "\n".join(lines)


def format_market_snapshot_hebrew(data: dict) -> str:
    """Format market snapshot for Agent 1 and free chat."""
    if not data:
        return ""

    lines = ["[Market Snapshot — TradingView]"]

    def fmt(key, label):
        val = data.get(key)
        if val:
            price = val.get("price", 0)
            change = val.get("change_percent", 0)
            emoji = "📈" if change >= 0 else "📉"
            lines.append(f"  {emoji} {label}: ${price:,.2f} ({change:+.2f}%)")

    fmt("SPY", "SPY")
    fmt("QQQ", "QQQ")
    fmt("^VIX", "VIX")
    fmt("BTC-USD", "BTC")
    fmt("GLD", "GLD")
    fmt("EURUSD=X", "EUR/USD")

    return "\n".join(lines)


def format_reddit_sentiment_hebrew(ticker: str, data: dict) -> str:
    """Format Reddit sentiment for Telegram context."""
    if not data:
        return ""

    score = data.get("sentiment_score", 0)
    total_posts = data.get("total_posts", 0)
    bullish = data.get("bullish_count", 0)
    bearish = data.get("bearish_count", 0)

    label = (
        "🟢 שורי מאוד" if score > 0.3 else
        "🟢 שורי" if score > 0.1 else
        "🔴 דובי מאוד" if score < -0.3 else
        "🔴 דובי" if score < -0.1 else
        "⚪ ניטרלי"
    )

    return (
        f"[Reddit Sentiment — {ticker}]\n"
        f"{label} | ציון: {score:+.2f}\n"
        f"פוסטים: {total_posts} | 🟢{bullish} שוריים | 🔴{bearish} דוביים"
    )


def format_backtest_comparison_hebrew(ticker: str, data: dict) -> str:
    """Format strategy comparison for /backtest command."""
    if not data:
        return ""

    strategies = data.get("strategies", [])
    if not strategies:
        return f"לא הצלחתי להריץ backtest על {ticker}"

    lines = [f"[Backtest Comparison — {ticker}]"]
    for i, s in enumerate(strategies[:6], 1):
        ret = s.get("total_return", 0)
        sharpe = s.get("sharpe_ratio", 0)
        wr = s.get("win_rate", 0)
        emoji = "📈" if ret >= 0 else "📉"
        lines.append(
            f"#{i} {s.get('strategy', '')}: {emoji}{ret:+.1f}% | "
            f"Sharpe: {sharpe:.2f} | Win Rate: {wr:.0f}%"
        )

    bh = data.get("buy_and_hold_return", 0)
    lines.append(f"Buy & Hold: {bh:+.1f}%")
    return "\n".join(lines)


# ── Auto-enrichment API (used by free_chat and smart_scanner) ─────────────────

def enrich_ticker_context(ticker: str) -> str:
    """
    Auto-enrichment for any ticker mentioned in free chat.
    Returns formatted string with TV signals, MTF, patterns, Reddit.
    Called from free_chat.py _fetch_stock_data().
    """
    parts = []

    tv_tech = get_tv_technical(ticker)
    if tv_tech:
        parts.append(format_tv_technical_hebrew(ticker, tv_tech))

    mtf = get_tv_multi_timeframe(ticker)
    if mtf:
        parts.append(format_multi_timeframe_hebrew(ticker, mtf))

    candles = get_tv_candlestick_patterns(ticker)
    if candles:
        fmt = format_candlestick_hebrew(ticker, candles)
        if fmt:
            parts.append(fmt)

    reddit = get_reddit_sentiment(ticker)
    if reddit:
        parts.append(format_reddit_sentiment_hebrew(ticker, reddit))

    return "\n\n".join(parts) if parts else ""


def get_market_context_for_agent1() -> str:
    """
    TradingView market snapshot for Agent 1 regime detection and free chat.
    """
    snap = get_market_snapshot()
    return format_market_snapshot_hebrew(snap) if snap else ""
