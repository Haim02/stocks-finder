"""
iv.py — IV Rank Calculator
Priority: Polygon → yfinance fallback
"""
import logging, os, math
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)
SYMBOLS = ["SPY", "QQQ", "NVDA", "TSLA", "AAPL"]


@dataclass
class IVResult:
    symbol: str
    price: float
    iv_current: float    # decimal (0.25 = 25%)
    iv_rank: float       # 0.0 to 1.0
    iv_min_52w: float
    iv_max_52w: float
    iv_label: str        # "HIGH" | "NORMAL" | "LOW"
    source: str


def _classify(iv_rank: float) -> str:
    if iv_rank > 0.6: return "HIGH"
    if iv_rank < 0.3: return "LOW"
    return "NORMAL"


def _rolling_hvs(closes: list) -> list:
    if len(closes) < 21:
        return []
    returns = [math.log(closes[i]/closes[i-1]) for i in range(1, len(closes))]
    hvs = []
    for i in range(20, len(returns)):
        chunk = returns[i-20:i]
        mean = sum(chunk)/20
        var = sum((r-mean)**2 for r in chunk)/20
        hvs.append(math.sqrt(var * 252))
    return hvs


def _iv_rank_from_history(current_iv: float, closes: list) -> tuple[float, float, float]:
    hvs = _rolling_hvs(closes)
    if not hvs:
        return 0.5, current_iv*0.6, current_iv*1.4
    iv_min, iv_max = min(hvs), max(hvs)
    if iv_max == iv_min:
        return 0.5, iv_min*100, iv_max*100
    rank = (current_iv - iv_min) / (iv_max - iv_min)
    return max(0.0, min(1.0, rank)), round(iv_min*100, 2), round(iv_max*100, 2)


def _from_polygon(symbol: str) -> Optional[IVResult]:
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        return None
    try:
        import requests
        r = requests.get(
            f"https://api.polygon.io/v3/snapshot/options/{symbol}",
            params={"apiKey": api_key, "limit": 50, "contract_type": "call"},
            timeout=10
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        ivs = [x["details"]["implied_volatility"] for x in results
               if x.get("details", {}).get("implied_volatility", 0) > 0.01]
        if not ivs:
            return None
        current_iv = sum(ivs) / len(ivs)

        r2 = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2025-04-01/2026-04-13",
            params={"apiKey": api_key, "limit": 252},
            timeout=10
        )
        r2.raise_for_status()
        bars = r2.json().get("results", [])
        closes = [b["c"] for b in bars if b.get("c")]
        if not closes:
            return None

        price = closes[-1]
        iv_rank, iv_min, iv_max = _iv_rank_from_history(current_iv, closes)
        return IVResult(symbol, round(price,2), round(current_iv,4),
                       round(iv_rank,3), iv_min, iv_max, _classify(iv_rank), "polygon")
    except Exception as e:
        logger.debug("Polygon failed %s: %s", symbol, e)
        return None


def _from_yfinance(symbol: str) -> Optional[IVResult]:
    try:
        from app.services.realtime_market_data import get_realtime_iv_data
        d = get_realtime_iv_data(symbol)
        if d.current_price <= 0:
            return None
        iv_rank = d.iv_rank / 100.0
        return IVResult(symbol, d.current_price, round(d.iv_current/100, 4),
                       round(iv_rank, 3), d.iv_low_52w, d.iv_high_52w,
                       _classify(iv_rank), "yfinance")
    except Exception as e:
        logger.debug("yfinance failed %s: %s", symbol, e)
        return None


def get_iv(symbol: str) -> Optional[IVResult]:
    """Get IV — tries Polygon → yfinance."""
    for fn in (_from_polygon, _from_yfinance):
        result = fn(symbol)
        if result:
            logger.info("IV %s: rank=%.2f label=%s src=%s",
                       symbol, result.iv_rank, result.iv_label, result.source)
            return result
    logger.warning("All IV sources failed for %s", symbol)
    return None
