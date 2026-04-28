"""
tradingview_service.py — TradingView Intelligence Layer
=======================================================
Uses tradingview-screener (pip package) for stock scanning.
No MCP server needed — direct Python import.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_cache: dict = {}
_CACHE_TTL = 600


def _get_cache(key: str):
    entry = _cache.get(key)
    if entry:
        data, ts = entry
        if time.time() - ts < _CACHE_TTL:
            return data
    return None


def _set_cache(key: str, data):
    _cache[key] = (data, time.time())


def get_tv_technical(ticker: str, exchange: str = "NASDAQ") -> Optional[dict]:
    """Get technical analysis for a single ticker."""
    cache_key = f"tv_tech_{ticker}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    try:
        from tradingview_screener import Query, col

        _, scanner = (
            Query()
            .select(
                "name", "close", "change", "volume",
                "RSI", "MACD.macd", "MACD.signal",
                "EMA20", "EMA50", "EMA200",
                "BB.upper", "BB.lower",
                "Recommend.All", "Recommend.MA", "Recommend.Other",
            )
            .where(col("name") == ticker)
            .set_markets("america")
            .limit(1)
            .get_scanner_data()
        )

        if scanner is None or scanner.empty:
            return None

        row = scanner.iloc[0]
        rec_score = float(row.get("Recommend.All", 0) or 0)

        if rec_score >= 0.5:
            recommendation = "STRONG_BUY"
        elif rec_score >= 0.1:
            recommendation = "BUY"
        elif rec_score <= -0.5:
            recommendation = "STRONG_SELL"
        elif rec_score <= -0.1:
            recommendation = "SELL"
        else:
            recommendation = "NEUTRAL"

        result = {
            "recommendation": recommendation,
            "rec_score": round(rec_score, 3),
            "rsi": round(float(row.get("RSI", 50) or 50), 1),
            "macd": round(float(row.get("MACD.macd", 0) or 0), 4),
            "close": round(float(row.get("close", 0) or 0), 2),
            "change_pct": round(float(row.get("change", 0) or 0), 2),
            "ema20": round(float(row.get("EMA20", 0) or 0), 2),
            "ema50": round(float(row.get("EMA50", 0) or 0), 2),
            "ema200": round(float(row.get("EMA200", 0) or 0), 2),
            "bb_upper": round(float(row.get("BB.upper", 0) or 0), 2),
            "bb_lower": round(float(row.get("BB.lower", 0) or 0), 2),
        }

        _set_cache(cache_key, result)
        logger.info("TV technical for %s: %s (%.2f)", ticker, recommendation, rec_score)
        return result

    except Exception as e:
        logger.debug("TV technical failed for %s: %s", ticker, e)
        return None


def scan_by_signal_type(
    signal: str = "oversold",
    exchange: str = "NASDAQ",
    limit: int = 10,
) -> list:
    """Scan stocks by signal type using tradingview-screener."""
    cache_key = f"tv_scan_{signal}_{exchange}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    try:
        from tradingview_screener import Query, col

        q = Query().select(
            "name", "close", "change", "volume", "RSI", "Recommend.All"
        ).set_markets("america")

        if signal == "oversold":
            q = q.where(col("RSI") < 35, col("volume") > 500000, col("close") > 5)
        elif signal == "overbought":
            q = q.where(col("RSI") > 70, col("volume") > 500000, col("close") > 5)
        elif signal == "strong_buy":
            q = q.where(col("Recommend.All") > 0.5, col("volume") > 500000)
        elif signal == "strong_sell":
            q = q.where(col("Recommend.All") < -0.5, col("volume") > 500000)
        elif signal == "trending_up":
            q = q.where(
                col("EMA20") > col("EMA50"),
                col("close") > col("EMA20"),
                col("volume") > 500000,
            )
        elif signal == "breakout":
            q = q.where(
                col("change") > 3,
                col("volume") > 1000000,
                col("RSI") > 50,
                col("RSI") < 75,
            )
        else:
            return []

        _, scanner = q.limit(limit).get_scanner_data()

        if scanner is None or scanner.empty:
            return []

        results = []
        for _, row in scanner.iterrows():
            rec = float(row.get("Recommend.All", 0) or 0)
            results.append({
                "symbol": str(row.get("name", "")),
                "price": round(float(row.get("close", 0) or 0), 2),
                "change_percent": round(float(row.get("change", 0) or 0), 2),
                "rsi": round(float(row.get("RSI", 50) or 50), 1),
                "recommendation": (
                    "STRONG_BUY" if rec >= 0.5 else
                    "BUY" if rec >= 0.1 else
                    "SELL" if rec <= -0.1 else "NEUTRAL"
                ),
                "volume": int(row.get("volume", 0) or 0),
            })

        _set_cache(cache_key, results)
        return results

    except Exception as e:
        logger.warning("TV scan failed (%s): %s", signal, e)
        return []


def get_market_snapshot() -> Optional[dict]:
    """Market snapshot using yfinance — SPY, VIX, QQQ, BTC, GLD."""
    cache_key = "tv_snapshot"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf

        tickers = {
            "SPY": "SPY",
            "QQQ": "QQQ",
            "^VIX": "VIX",
            "BTC-USD": "BTC",
            "GLD": "GLD",
            "EURUSD=X": "EUR/USD",
        }

        result = {}
        for symbol, label in tickers.items():
            try:
                hist = yf.Ticker(symbol).history(period="2d")
                if not hist.empty and len(hist) >= 2:
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    change = round((price / prev - 1) * 100, 2)
                    result[label] = {
                        "price": round(price, 2),
                        "change_percent": change,
                    }
            except Exception:
                continue

        _set_cache(cache_key, result)
        return result

    except Exception as e:
        logger.debug("Market snapshot failed: %s", e)
        return None


def enrich_ticker_context(ticker: str) -> str:
    """Auto-enrichment — TV technical for any ticker in free chat."""
    parts = []

    tv = get_tv_technical(ticker)
    if tv:
        parts.append(format_tv_technical_hebrew(ticker, tv))

    # Add GEX + A/D for index ETFs
    if ticker.upper() in ("SPY", "QQQ", "SPX", "IWM", "/ES"):
        try:
            from app.services.gex_calculator import calculate_gex, format_gex_hebrew
            gex = calculate_gex("SPY")
            if gex:
                parts.append(format_gex_hebrew(gex))
        except Exception:
            pass

        try:
            from app.services.advance_decline import get_ad_line, format_ad_line_hebrew
            ad = get_ad_line()
            if ad:
                parts.append(format_ad_line_hebrew(ad))
        except Exception:
            pass

    return "\n\n".join(parts) if parts else ""


def get_market_context_for_agent1() -> str:
    """Market context for Agent 1."""
    snap = get_market_snapshot()
    if snap:
        return format_market_snapshot_hebrew(snap)
    return ""


def format_tv_technical_hebrew(ticker: str, data: dict) -> str:
    if not data:
        return ""

    rec = data.get("recommendation", "NEUTRAL")
    rec_emoji = {
        "STRONG_BUY": "🚀 STRONG BUY",
        "BUY": "🟢 BUY",
        "NEUTRAL": "➡️ NEUTRAL",
        "SELL": "🔴 SELL",
        "STRONG_SELL": "🔴🔴 STRONG SELL",
    }.get(rec, rec)

    rsi = data.get("rsi", 50)
    rsi_note = "⚠️ Overbought" if rsi > 70 else ("⚠️ Oversold" if rsi < 30 else "✅ Normal")
    price = data.get("close", 0)
    change = data.get("change_pct", 0)
    change_emoji = "📈" if change >= 0 else "📉"

    return (
        f"[TradingView — {ticker}]\n"
        f"המלצה: {rec_emoji}\n"
        f"מחיר: ${price} {change_emoji}{change:+.1f}%\n"
        f"RSI: {rsi} {rsi_note}\n"
        f"EMA20: ${data.get('ema20', 0)} | EMA50: ${data.get('ema50', 0)}"
    )


def format_market_snapshot_hebrew(data: dict) -> str:
    if not data:
        return ""

    lines = ["[Market Snapshot]"]
    for label, vals in data.items():
        price = vals.get("price", 0)
        change = vals.get("change_percent", 0)
        emoji = "📈" if change >= 0 else "📉"
        lines.append(f"  {emoji} {label}: ${price:,.2f} ({change:+.2f}%)")

    return "\n".join(lines)


def format_backtest_comparison_hebrew(ticker: str, data: dict) -> str:
    return ""  # Placeholder — backtest_engine.py handles this
