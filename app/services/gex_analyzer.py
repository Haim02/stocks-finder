"""
Gamma Exposure (GEX) Analyzer
================================
Calculates dealer gamma exposure from the options chain to determine
whether the market is in a "positive gamma" or "negative gamma" regime.

Methodology (standard GEX model):
  - Dealers are assumed SHORT calls (retail buys calls) → negative GEX per call
  - Dealers are assumed SHORT puts  (retail buys puts)  → positive GEX per put
  - GEX per strike = (put_OI × put_gamma − call_OI × call_gamma) × 100 × price

Key levels:
  - Gamma Wall:   strike with highest positive GEX (price magnet / mean-reversion)
  - Zero GEX:     strike where net GEX sign crosses zero
  - Negative Zone: price below zero line — dealers must chase moves (vol expands)

References: SpotGamma, SqueezeMetrics GEX methodology
"""

import logging
import math
from datetime import datetime, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)


# ── Black-Scholes Gamma ────────────────────────────────────────────────────────

def _bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes gamma for a single option.
    S     = underlying price
    K     = strike price
    T     = time to expiry in years (DTE / 365)
    r     = risk-free rate
    sigma = implied volatility (decimal, e.g. 0.30)
    Returns gamma per 1 share.
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    try:
        d1    = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        gamma = math.exp(-0.5 * d1 ** 2) / (math.sqrt(2 * math.pi) * S * sigma * math.sqrt(T))
        return gamma
    except Exception:
        return 0.0


# ── Main GEX Engine ────────────────────────────────────────────────────────────

def calculate_gex(ticker: str, max_dte: int = 45) -> dict:
    """
    Calculate full Gamma Exposure (GEX) map for a ticker.

    Args:
        ticker:  stock/ETF symbol (e.g. "SPY")
        max_dte: only include expirations within this many days

    Returns dict with:
        ticker          : str
        current_price   : float
        gamma_wall      : float  — strike with highest positive GEX (magnet)
        zero_gex_line   : float  — strike where GEX crosses zero
        total_gex       : float  — sum of all GEX (in millions)
        regime          : str    — "positive" | "negative" | "transitional"
        regime_label    : str    — Hebrew label with emoji
        recommendation  : str    — strategy recommendation in Hebrew
        top_strikes     : list   — top 5 strikes by abs(GEX) with details
        gex_by_strike   : dict   — full GEX map {strike: gex_millions}
        chart_ascii     : str    — ASCII bar chart
        expiries_used   : int
        error           : str | None
    """
    try:
        stock         = yf.Ticker(ticker)
        current_price = stock.fast_info.last_price
        if not current_price:
            hist          = stock.history(period="1d")
            current_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0
        if not current_price:
            return {"error": f"Cannot fetch price for {ticker}"}

        today        = datetime.today().date()
        cutoff       = today + timedelta(days=max_dte)
        expiries     = stock.options
        if not expiries:
            return {"error": f"No options data available for {ticker}"}

        # Filter to expirations within max_dte
        valid_expiries = []
        for exp in expiries:
            try:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                if today <= exp_date <= cutoff:
                    valid_expiries.append((exp, exp_date))
            except Exception:
                continue

        if not valid_expiries:
            return {"error": f"No expirations within {max_dte} days for {ticker}"}

        # Risk-free rate
        try:
            tbill = yf.Ticker("^IRX")
            r     = float(tbill.fast_info.last_price) / 100 if tbill.fast_info.last_price else 0.05
        except Exception:
            r = 0.05

        # ── Aggregate GEX across all valid expiries ──────────────────────
        gex_map: dict[float, float] = {}

        for exp_str, exp_date in valid_expiries:
            T = max((exp_date - today).days, 1) / 365.0

            try:
                chain = stock.option_chain(exp_str)
            except Exception:
                continue

            # CALLS — dealer short calls → negative GEX
            if chain.calls is not None and not chain.calls.empty:
                for _, row in chain.calls.iterrows():
                    try:
                        K     = float(row["strike"])
                        oi    = float(row.get("openInterest") or 0)
                        sigma = float(row.get("impliedVolatility") or 0)
                        if oi < 1 or sigma < 0.01:
                            continue
                        gamma = _bs_gamma(current_price, K, T, r, sigma)
                        gex_map[K] = gex_map.get(K, 0.0) + (-gamma * oi * 100 * current_price)
                    except Exception:
                        continue

            # PUTS — dealer short puts → positive GEX
            if chain.puts is not None and not chain.puts.empty:
                for _, row in chain.puts.iterrows():
                    try:
                        K     = float(row["strike"])
                        oi    = float(row.get("openInterest") or 0)
                        sigma = float(row.get("impliedVolatility") or 0)
                        if oi < 1 or sigma < 0.01:
                            continue
                        gamma = _bs_gamma(current_price, K, T, r, sigma)
                        gex_map[K] = gex_map.get(K, 0.0) + (gamma * oi * 100 * current_price)
                    except Exception:
                        continue

        if not gex_map:
            return {"error": "Could not calculate GEX — no valid options data"}

        sorted_strikes = sorted(gex_map.keys())
        total_gex      = sum(v for v in gex_map.values() if not math.isnan(v))

        # Gamma Wall = strike with highest positive GEX
        positive_strikes = {k: v for k, v in gex_map.items() if v > 0}
        gamma_wall       = (
            max(positive_strikes, key=positive_strikes.get)
            if positive_strikes else current_price
        )

        # Zero GEX line
        zero_gex_line = _find_zero_crossing(gex_map, sorted_strikes, current_price)

        # Top 5 by abs(GEX)
        top_5 = sorted(gex_map.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        top_strikes = [
            {
                "strike": k,
                "gex":    round(v / 1_000_000, 2),
                "type":   "חיובי (תמיכה)" if v > 0 else "שלילי (דחיפה)",
            }
            for k, v in top_5
        ]

        regime, regime_label, recommendation = _classify_regime(
            current_price, gamma_wall, zero_gex_line, total_gex
        )

        chart = _build_ascii_chart(gex_map, current_price, gamma_wall, zero_gex_line)

        return {
            "ticker":         ticker,
            "current_price":  round(current_price, 2),
            "gamma_wall":     round(gamma_wall, 2),
            "zero_gex_line":  round(zero_gex_line, 2),
            "total_gex":      round(total_gex / 1_000_000, 2),
            "regime":         regime,
            "regime_label":   regime_label,
            "recommendation": recommendation,
            "top_strikes":    top_strikes,
            "gex_by_strike":  {k: round(v / 1_000_000, 3) for k, v in gex_map.items()},
            "chart_ascii":    chart,
            "expiries_used":  len(valid_expiries),
            "error":          None,
        }

    except Exception as e:
        logger.exception("calculate_gex(%s) failed", ticker)
        return {"error": str(e)}


def _find_zero_crossing(
    gex_map: dict, sorted_strikes: list, current_price: float
) -> float:
    """Find the strike closest to the zero-GEX crossing near current price."""
    if not sorted_strikes:
        return current_price

    best_zero  = current_price
    prev_strike = sorted_strikes[0]
    prev_gex    = gex_map.get(prev_strike, 0)

    for strike in sorted_strikes[1:]:
        curr_gex = gex_map.get(strike, 0)
        if prev_gex * curr_gex < 0:   # sign change = zero crossing
            candidate = (prev_strike + strike) / 2
            if abs(candidate - current_price) < abs(best_zero - current_price):
                best_zero = candidate
        prev_strike = strike
        prev_gex    = curr_gex

    return best_zero


def _classify_regime(
    price: float,
    gamma_wall: float,
    zero_line: float,
    total_gex: float,
) -> tuple[str, str, str]:
    """Classify GEX regime. Returns (code, hebrew_label, recommendation)."""
    gex_m = total_gex / 1_000_000

    if gex_m > 0 and price >= zero_line:
        return (
            "positive",
            "🟢 גמא חיובי — השוק מרוסן",
            (
                "סביבת מכירת פרמיה אידיאלית.\n"
                "דילרים מבלמים תנועות — קונים בירידות ומוכרים בעליות.\n"
                "✅ Iron Condor / Bull Put Spread / Bear Call Spread"
            ),
        )
    elif gex_m < 0 or price < zero_line:
        return (
            "negative",
            "🔴 גמא שלילי — השוק תנודתי",
            (
                "אל תמכור פרמיה עכשיו!\n"
                "דילרים רצים אחרי המחיר — תנועות מואצות בשני הכיוונים.\n"
                "⚠️ המתן לייצוב. שקול Long Straddle / Long Puts אם מגמה ברורה."
            ),
        )
    else:
        return (
            "transitional",
            "🟡 גמא מעברי — זהירות",
            (
                "מחיר בין קו האפס לגמא וול.\n"
                "נטייה למכירת פרמיה אבל צמצם כנפיים והקטן גודל.\n"
                "🟡 Bull Put Spread צר / Iron Condor עם כנפיים רחבות."
            ),
        )


def _build_ascii_chart(
    gex_map: dict,
    current_price: float,
    gamma_wall: float,
    zero_line: float,
    n_bars: int = 15,
) -> str:
    """Build a simple ASCII bar chart of GEX by strike."""
    if not gex_map:
        return ""

    all_strikes  = sorted(gex_map.keys())
    near_strikes = [s for s in all_strikes if abs(s - current_price) / current_price < 0.08]
    if not near_strikes:
        near_strikes = all_strikes

    mid_idx = len(near_strikes) // 2
    start   = max(0, mid_idx - n_bars // 2)
    sample  = near_strikes[start: start + n_bars]

    max_abs  = max(abs(gex_map.get(s, 0)) for s in sample) or 1
    bar_width = 12
    lines     = ["```", f"GEX Map — {current_price:.0f} (מחיר נוכחי)"]
    lines.append("─" * 38)

    for strike in sample:
        gex     = gex_map.get(strike, 0)
        bar_len = int(abs(gex) / max_abs * bar_width)
        bar     = "█" * bar_len
        sign    = "+" if gex >= 0 else "-"
        bar_str = f"{sign}{bar:<{bar_width}}"
        gex_m   = gex / 1_000_000

        tag = ""
        if abs(strike - gamma_wall) < 0.5:
            tag = " ← 🧲 גמא וול"
        elif abs(strike - zero_line) < 1.0:
            tag = " ← ⚡ קו האפס"
        elif abs(strike - current_price) < 1.0:
            tag = " ← 📍 מחיר"

        lines.append(f"${strike:>6.0f}  {bar_str}  {gex_m:+.1f}M{tag}")

    lines.append("─" * 38)
    lines.append("```")
    return "\n".join(lines)


# ── Telegram formatter ─────────────────────────────────────────────────────────

def format_gex_telegram(result: dict) -> str:
    """Format GEX analysis result as Hebrew Telegram Markdown message."""
    if result.get("error"):
        return f"❌ שגיאת GEX: {result['error']}"

    top_lines = []
    for i, s in enumerate(result.get("top_strikes", []), 1):
        top_lines.append(
            f"   {i}. Strike ${s['strike']:.0f} | "
            f"GEX: {s['gex']:+.1f}M | {s['type']}"
        )

    top_str    = "\n".join(top_lines) if top_lines else "   אין נתונים"
    chart      = result.get("chart_ascii", "")
    total_sign = "+" if result["total_gex"] >= 0 else ""

    return (
        f"🎯 *GEX Analysis — {result['ticker']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💹 מחיר נוכחי: `${result['current_price']}`\n"
        f"🧲 גמא וול:    `${result['gamma_wall']}`\n"
        f"⚡ קו האפס:   `${result['zero_gex_line']}`\n"
        f"📊 סה״כ GEX:  `{total_sign}{result['total_gex']:.1f}M`\n"
        f"📅 פקיעות שנסרקו: `{result['expiries_used']}`\n\n"
        f"🏷️ *משטר נוכחי:* {result['regime_label']}\n\n"
        f"💡 *המלצה:*\n{result['recommendation']}\n\n"
        f"🔝 *Top 5 Strikes:*\n{top_str}\n\n"
        + (chart if chart else "")
    )
