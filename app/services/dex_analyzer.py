"""
dex_analyzer.py — Delta Exposure (DEX) Support/Resistance Monitor
==================================================================

Computes per-strike Dollar Delta Exposure from the option chain:

    DEX per strike = Delta × OI × 100 × Spot
    Calls → positive DEX, Puts → negative DEX (put delta is negative)

Interpretation for intraday SPX 0DTE trading:
- Strikes BELOW spot with heavy negative DEX (put concentration)
  act as SUPPORT — dealers hedge by buying as price approaches.
- Strikes ABOVE spot with heavy positive DEX (call concentration)
  act as RESISTANCE — dealers hedge by selling as price approaches.

The monitor runs intraday (every 30 min during the US session),
compares against the previous snapshot stored in MongoDB, and
alerts on Telegram ONLY when:
- A NEW support/resistance level appears (strike not seen before today)
- An existing level strengthens by more than 30%
- Spot crosses through a previously reported level

Symbols: SPX (via ^SPX on yfinance, SPY×10 fallback), focused on
the nearest 2 expirations (0DTE + next) where delta hedging matters.
"""

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

_cache: dict = {}
_DEX_TTL = 600  # 10 minutes

# How much stronger a level must get before we re-alert (fraction)
STRENGTHEN_THRESHOLD = 0.30
# Levels further than this from spot are ignored (fraction of spot)
MAX_DISTANCE_PCT = 0.03
# Number of levels reported on each side
TOP_N_LEVELS = 3


@dataclass
class DEXLevel:
    strike: float
    dex: float          # $ delta exposure at this strike (billions)
    kind: str           # "SUPPORT" | "RESISTANCE"
    dist_pct: float     # distance from spot in %


@dataclass
class DEXResult:
    symbol: str
    spot_price: float
    calculation_time: str
    total_dex: float                       # net $ DEX ($B)
    supports: list = field(default_factory=list)      # list[DEXLevel]
    resistances: list = field(default_factory=list)   # list[DEXLevel]


def _bs_delta(S: float, K: float, T: float, sigma: float, is_call: bool,
              r: float = 0.045) -> float:
    """Black-Scholes delta."""
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        cdf = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
        return cdf if is_call else cdf - 1.0
    except Exception:
        return 0.0


def _safe_num(val) -> float:
    try:
        v = float(val or 0)
        return v if v == v else 0.0  # NaN check
    except (TypeError, ValueError):
        return 0.0


def _yf_symbol(symbol: str) -> str:
    return {"SPX": "^SPX", "NDX": "^NDX"}.get(symbol.upper(), symbol)


def calculate_dex(symbol: str = "SPX") -> Optional[DEXResult]:
    """
    Full per-strike DEX profile for the nearest 2 expirations.
    Cached for 10 minutes.
    """
    cache_key = f"dex_{symbol}"
    cached = _cache.get(cache_key)
    if cached:
        data, ts = cached
        if time.time() - ts < _DEX_TTL:
            return data

    try:
        import yfinance as yf

        ticker = yf.Ticker(_yf_symbol(symbol))
        hist = ticker.history(period="1d")
        if hist.empty:
            logger.warning("DEX: no price history for %s", symbol)
            return None
        spot = float(hist["Close"].iloc[-1])

        expirations = ticker.options[:2]  # 0DTE + next expiration
        if not expirations:
            logger.warning("DEX: no option expirations for %s", symbol)
            return None

        today = date.today()
        strike_dex: dict[float, float] = {}

        for exp in expirations:
            exp_date = date.fromisoformat(exp)
            T = max((exp_date - today).days / 365, 1 / 365 / 2)  # half-day min for 0DTE

            try:
                chain = ticker.option_chain(exp)
            except Exception as e:
                logger.debug("DEX chain fetch failed %s %s: %s", symbol, exp, e)
                continue

            for df, is_call in ((chain.calls, True), (chain.puts, False)):
                for _, row in df.iterrows():
                    K = _safe_num(row.get("strike"))
                    oi = _safe_num(row.get("openInterest"))
                    if oi <= 0:
                        oi = _safe_num(row.get("volume"))  # OI lags in the morning
                    iv = _safe_num(row.get("impliedVolatility")) or 0.25
                    if K <= 0 or oi <= 0:
                        continue
                    if abs(K - spot) / spot > MAX_DISTANCE_PCT:
                        continue
                    delta = _bs_delta(spot, K, T, iv, is_call)
                    dex_b = delta * oi * 100 * spot / 1e9
                    strike_dex[K] = strike_dex.get(K, 0.0) + dex_b

        if not strike_dex:
            logger.warning("DEX: empty profile for %s", symbol)
            return None

        total_dex = sum(strike_dex.values())

        # Supports: below spot, most negative DEX (put concentration)
        below = {k: v for k, v in strike_dex.items() if k < spot and v < 0}
        supports = sorted(below.items(), key=lambda kv: kv[1])[:TOP_N_LEVELS]

        # Resistances: above spot, most positive DEX (call concentration)
        above = {k: v for k, v in strike_dex.items() if k > spot and v > 0}
        resistances = sorted(above.items(), key=lambda kv: -kv[1])[:TOP_N_LEVELS]

        result = DEXResult(
            symbol=symbol,
            spot_price=round(spot, 2),
            calculation_time=datetime.now().strftime("%d/%m %H:%M"),
            total_dex=round(total_dex, 3),
            supports=[
                DEXLevel(k, round(v, 3), "SUPPORT", round((k / spot - 1) * 100, 2))
                for k, v in supports
            ],
            resistances=[
                DEXLevel(k, round(v, 3), "RESISTANCE", round((k / spot - 1) * 100, 2))
                for k, v in resistances
            ],
        )

        _cache[cache_key] = (result, time.time())
        logger.info(
            "DEX %s: spot=%.0f supports=%s resistances=%s",
            symbol, spot,
            [l.strike for l in result.supports],
            [l.strike for l in result.resistances],
        )
        return result

    except Exception as e:
        logger.error("DEX calculation failed for %s: %s", symbol, e)
        return None


# ── Snapshot diffing (MongoDB) ────────────────────────────────────────────────

def _levels_to_doc(levels: list) -> list:
    return [{"strike": l.strike, "dex": l.dex} for l in levels]


def _detect_changes(result: DEXResult, prev: Optional[dict]) -> list[str]:
    """
    Compare current levels against the previous snapshot.
    Returns Hebrew change descriptions (empty list = nothing new).
    """
    changes: list[str] = []

    prev_supports = {d["strike"]: d["dex"] for d in (prev or {}).get("supports", [])}
    prev_resists = {d["strike"]: d["dex"] for d in (prev or {}).get("resistances", [])}

    for level in result.supports:
        old = prev_supports.get(level.strike)
        if old is None:
            changes.append(
                f"🟢 תמיכת Delta חדשה: `{level.strike:,.0f}` "
                f"({level.dist_pct:+.1f}%, DEX {level.dex:+.2f}B)"
            )
        elif abs(level.dex) > abs(old) * (1 + STRENGTHEN_THRESHOLD):
            changes.append(
                f"🟢 תמיכה ב-`{level.strike:,.0f}` התחזקה: "
                f"{old:+.2f}B → {level.dex:+.2f}B"
            )

    for level in result.resistances:
        old = prev_resists.get(level.strike)
        if old is None:
            changes.append(
                f"🔴 התנגדות Delta חדשה: `{level.strike:,.0f}` "
                f"({level.dist_pct:+.1f}%, DEX {level.dex:+.2f}B)"
            )
        elif abs(level.dex) > abs(old) * (1 + STRENGTHEN_THRESHOLD):
            changes.append(
                f"🔴 התנגדות ב-`{level.strike:,.0f}` התחזקה: "
                f"{old:+.2f}B → {level.dex:+.2f}B"
            )

    # Spot crossed a previously reported level since last snapshot
    prev_spot = (prev or {}).get("spot_price")
    if prev_spot:
        for strike in list(prev_supports) + list(prev_resists):
            lo, hi = min(prev_spot, result.spot_price), max(prev_spot, result.spot_price)
            if lo < strike < hi:
                direction = "מעלה ⬆️" if result.spot_price > prev_spot else "מטה ⬇️"
                changes.append(
                    f"⚡ המחיר חצה רמת Delta `{strike:,.0f}` כלפי {direction} "
                    f"(spot: {prev_spot:,.0f} → {result.spot_price:,.0f})"
                )

    return changes


def check_dex_changes(symbol: str = "SPX") -> Optional[str]:
    """
    Calculate DEX, diff against today's previous snapshot, persist the new one.
    Returns a formatted Hebrew alert if something changed, else None.
    """
    result = calculate_dex(symbol)
    if not result:
        return None

    prev = None
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        today_str = date.today().isoformat()

        prev = db["dex_snapshots"].find_one(
            {"symbol": symbol, "trade_date": today_str},
            sort=[("created_at", -1)],
        )

        db["dex_snapshots"].insert_one({
            "symbol": symbol,
            "trade_date": today_str,
            "spot_price": result.spot_price,
            "total_dex": result.total_dex,
            "supports": _levels_to_doc(result.supports),
            "resistances": _levels_to_doc(result.resistances),
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        logger.warning("DEX snapshot persistence failed: %s", e)

    changes = _detect_changes(result, prev)

    if prev is None:
        # First snapshot of the day — send the full opening picture
        return format_dex_hebrew(result)

    if not changes:
        return None

    return (
        f"⚡ *עדכון DEX תוך-יומי — {result.symbol}*\n"
        f"💵 Spot: `{result.spot_price:,.2f}` | {result.calculation_time}\n"
        f"──────────────────────────\n"
        + "\n".join(changes)
        + f"\n──────────────────────────\n{_levels_summary(result)}"
    )


def _levels_summary(r: DEXResult) -> str:
    res_lines = [
        f"  🔴 `{l.strike:,.0f}` ({l.dist_pct:+.1f}%) — {l.dex:+.2f}B"
        for l in r.resistances
    ]
    sup_lines = [
        f"  🟢 `{l.strike:,.0f}` ({l.dist_pct:+.1f}%) — {l.dex:+.2f}B"
        for l in r.supports
    ]
    return (
        "*התנגדויות (Call Delta):*\n" + ("\n".join(res_lines) or "  אין") +
        "\n*תמיכות (Put Delta):*\n" + ("\n".join(sup_lines) or "  אין")
    )


def format_dex_hebrew(r: DEXResult) -> str:
    """Full DEX report for Telegram."""
    bias = "🟢 חיובי (לחץ קנייה של Dealers)" if r.total_dex > 0 else \
           "🔴 שלילי (לחץ מכירה של Dealers)"
    return (
        f"📊 *DEX — Delta Exposure — {r.symbol}*\n"
        f"💵 Spot: `{r.spot_price:,.2f}` | {r.calculation_time}\n"
        f"──────────────────────────\n"
        f"💰 Net DEX: `{r.total_dex:+.2f}B` — {bias}\n\n"
        f"{_levels_summary(r)}\n"
        f"──────────────────────────\n"
        f"💡 תמיכות = ריכוזי Put OI מתחת למחיר (Dealers קונים בהתקרבות)\n"
        f"💡 התנגדויות = ריכוזי Call OI מעל למחיר (Dealers מוכרים בהתקרבות)"
    )


# ── Scheduler entry point ─────────────────────────────────────────────────────

def run_dex_monitor_sync() -> None:
    """
    APScheduler job: intraday DEX support/resistance monitor for SPX.
    Sends a Telegram alert only when levels change (or first run of the day).
    """
    try:
        alert = check_dex_changes("SPX")
        if alert:
            from app.agent.telegram_bot import notify_trade
            notify_trade(alert)
            logger.info("DEX alert sent")
        else:
            logger.info("DEX monitor: no level changes")
    except Exception:
        logger.exception("DEX monitor run failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = calculate_dex("SPX")
    if res:
        print(format_dex_hebrew(res))
