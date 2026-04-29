"""
realtime_stream.py — Real-Time Price Streaming via yfinance WebSocket
=====================================================================

Replaces delayed yfinance.history() calls with live prices for
time-critical operations: News Alerts, 0DTE Scanner, Free Chat.

yfinance v1.1.0+ supports WebSocket. If unavailable, falls back
to yfinance history() (15-minute delay) transparently.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory price cache: {ticker: (price, timestamp)}
_price_cache: dict = {}
_LIVE_TTL = 30  # seconds — refresh if older

_WS_AVAILABLE: Optional[bool] = None  # None = untested


def _check_ws_available() -> bool:
    global _WS_AVAILABLE
    if _WS_AVAILABLE is not None:
        return _WS_AVAILABLE
    try:
        from yfinance import WebSocket  # noqa: F401
        _WS_AVAILABLE = True
        logger.info("yfinance WebSocket available")
    except ImportError:
        _WS_AVAILABLE = False
        logger.info("yfinance WebSocket not available — using history fallback")
    return _WS_AVAILABLE


def get_live_price(ticker: str) -> Optional[float]:
    """
    Get the most current price available.
    Priority:
    1. In-memory cache if fresh (< 30s)
    2. yfinance WebSocket
    3. yfinance history() fallback (15-min delay)
    """
    cached = _price_cache.get(ticker)
    if cached:
        price, ts = cached
        if time.time() - ts < _LIVE_TTL:
            logger.debug("Cache hit for %s: $%.2f (%.0fs old)", ticker, price, time.time() - ts)
            return price

    if _check_ws_available():
        price = _fetch_via_websocket(ticker)
        if price and price > 0:
            _price_cache[ticker] = (price, time.time())
            return price

    return _fetch_via_history(ticker)


def _fetch_via_websocket(ticker: str, timeout: float = 3.0) -> Optional[float]:
    """Fetch price via yfinance WebSocket (synchronous)."""
    try:
        import yfinance as yf

        result: dict = {"price": None}

        def on_message(data):
            if isinstance(data, dict):
                price = (
                    data.get("regularMarketPrice")
                    or data.get("price")
                    or data.get("lastPrice")
                )
                if price and float(price) > 0:
                    result["price"] = float(price)

        ws = yf.WebSocket()
        ws.subscribe([ticker])

        start = time.time()
        while time.time() - start < timeout:
            data = ws.get_data()
            if data:
                on_message(data)
                if result["price"]:
                    break
            time.sleep(0.1)

        ws.close()

        if result["price"]:
            logger.info("WebSocket price for %s: $%.2f", ticker, result["price"])
            _price_cache[ticker] = (result["price"], time.time())
            return result["price"]

    except Exception as e:
        logger.debug("WebSocket fetch failed for %s: %s", ticker, e)

    return None


def _fetch_via_history(ticker: str) -> Optional[float]:
    """Fallback: yfinance history (up to 15-min delay)."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            _price_cache[ticker] = (price, time.time() - 900)  # mark as 15-min old
            logger.debug("History price for %s: $%.2f (15min delay)", ticker, price)
            return price
    except Exception as e:
        logger.debug("History fetch failed for %s: %s", ticker, e)
    return None


def get_live_prices_batch(tickers: list) -> dict:
    """Get live prices for multiple tickers efficiently."""
    results = {}
    fresh_needed = []

    for ticker in tickers:
        cached = _price_cache.get(ticker)
        if cached:
            price, ts = cached
            if time.time() - ts < _LIVE_TTL:
                results[ticker] = price
                continue
        fresh_needed.append(ticker)

    if not fresh_needed:
        return results

    # Batch WebSocket if available
    if _check_ws_available() and fresh_needed:
        try:
            import yfinance as yf
            ws = yf.WebSocket()
            ws.subscribe(fresh_needed)
            start = time.time()
            while time.time() - start < 5.0 and len(results) < len(tickers):
                data = ws.get_data()
                if data and isinstance(data, dict):
                    symbol = data.get("id") or data.get("symbol", "")
                    price = data.get("regularMarketPrice") or data.get("price")
                    if symbol in fresh_needed and price:
                        p = float(price)
                        results[symbol] = p
                        _price_cache[symbol] = (p, time.time())
                time.sleep(0.1)
            ws.close()
        except Exception as e:
            logger.debug("Batch WebSocket failed: %s", e)

    # History fallback for any still missing
    for ticker in fresh_needed:
        if ticker not in results:
            price = _fetch_via_history(ticker)
            if price:
                results[ticker] = price

    return results


def format_live_price_note(ticker: str, price: float) -> str:
    """Price string with freshness indicator."""
    cached = _price_cache.get(ticker)
    if cached:
        _, ts = cached
        age = time.time() - ts
        if age < 30:
            return f"${price:.2f} 🟢 חי"
        elif age < 300:
            return f"${price:.2f} 🟡 עדכני ({int(age/60)} דק')"
        else:
            return f"${price:.2f} ⚪ delay 15 דקות"
    return f"${price:.2f}"
