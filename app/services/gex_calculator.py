"""
gex_calculator.py — Gamma Exposure (GEX) Calculator
=====================================================

Based on SpotGamma's published methodology:
https://spotgamma.com/gamma-exposure-gex/

Formula:
GEX per strike = Gamma × OI × 100 × Spot² × 0.01
Calls = positive GEX (dealers long gamma)
Puts  = negative GEX (dealers short gamma — MULTIPLY BY -1)

Key Levels:
- Zero Gamma:  price where net GEX crosses from positive to negative
- Call Wall:   strike with highest net call gamma (resistance ceiling)
- Put Wall:    strike with highest net put gamma (support floor)
- Gamma Flip:  Zero Gamma — the regime change line

When ABOVE Zero Gamma: dealers stabilize market → sell rallies, buy dips
When BELOW Zero Gamma: dealers amplify moves → sell into drops, buy into rallies

Note: This is a "naive" GEX model (uses prior-day OI, single snapshot).
SpotGamma's paid service uses intraday OI updates + 4 expirations + dealer/customer split.
Our model covers nearest 2-3 expirations including 0DTE.
"""

import logging
import math
import time
from dataclasses import dataclass
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

_cache: dict = {}
_GEX_TTL = 900  # 15 minutes


@dataclass
class GEXResult:
    symbol: str
    spot_price: float
    calculation_time: str

    # Key levels
    zero_gamma: float         # Gamma flip — the most important level
    call_wall: float          # Highest call gamma strike (resistance)
    put_wall: float           # Highest put gamma strike (support)
    vol_trigger: float        # Estimated vol trigger (above put wall)

    # Regime
    net_gex: float            # Total net GEX in $ billions
    gamma_regime: str         # "POSITIVE" | "NEGATIVE"
    regime_note: str          # Hebrew explanation

    # Distances from spot
    dist_to_call_wall: float  # % to resistance
    dist_to_put_wall: float   # % to support
    dist_to_zero_gamma: float # % to gamma flip

    # Profile (for chart)
    strikes: list
    gex_profile: list         # GEX at each strike ($B)

    # Interpretation
    interpretation: str
    strategy_implication: str


def _black_scholes_gamma(S: float, K: float, T: float,
                          r: float, sigma: float) -> float:
    """Calculate option gamma using Black-Scholes."""
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        return math.exp(-0.5 * d1 ** 2) / (math.sqrt(2 * math.pi) * S * sigma * math.sqrt(T))
    except Exception:
        return 0.0


def calculate_gex(symbol: str = "SPY") -> Optional[GEXResult]:
    """
    Calculate full GEX profile for a symbol.
    Returns key levels: Zero Gamma, Call Wall, Put Wall.
    """
    cached = _cache.get(f"gex_{symbol}")
    if cached:
        data, ts = cached
        if time.time() - ts < _GEX_TTL:
            return data

    try:
        import yfinance as yf
        import numpy as np

        stock = yf.Ticker(symbol)

        hist = stock.history(period="1d")
        if hist.empty:
            return None
        spot = float(hist["Close"].iloc[-1])

        today = date.today()
        r = 0.045  # risk-free rate

        strike_gex: dict = {}
        call_gex_by_strike: dict = {}
        put_gex_by_strike: dict = {}

        expirations = stock.options[:4]  # nearest 4 expirations

        for exp in expirations:
            exp_date = date.fromisoformat(exp)
            T = max((exp_date - today).days / 365, 1 / 365)

            try:
                chain = stock.option_chain(exp)

                for _, row in chain.calls.iterrows():
                    K = float(row.get("strike", 0))
                    oi = int(row.get("openInterest", 0) or 0)
                    iv = float(row.get("impliedVolatility", 0.3) or 0.3)
                    if K <= 0 or oi == 0 or iv <= 0:
                        continue
                    if abs(K - spot) / spot > 0.15:
                        continue
                    gamma = _black_scholes_gamma(spot, K, T, r, iv)
                    gex_b = gamma * oi * 100 * (spot ** 2) * 0.01 / 1e9
                    strike_gex[K] = strike_gex.get(K, 0) + gex_b
                    call_gex_by_strike[K] = call_gex_by_strike.get(K, 0) + gex_b

                for _, row in chain.puts.iterrows():
                    K = float(row.get("strike", 0))
                    oi = int(row.get("openInterest", 0) or 0)
                    iv = float(row.get("impliedVolatility", 0.3) or 0.3)
                    if K <= 0 or oi == 0 or iv <= 0:
                        continue
                    if abs(K - spot) / spot > 0.15:
                        continue
                    gamma = _black_scholes_gamma(spot, K, T, r, iv)
                    gex_b = gamma * oi * 100 * (spot ** 2) * 0.01 / 1e9
                    strike_gex[K] = strike_gex.get(K, 0) - gex_b  # NEGATIVE
                    put_gex_by_strike[K] = put_gex_by_strike.get(K, 0) + gex_b

            except Exception as e:
                logger.debug("GEX chain failed for %s %s: %s", symbol, exp, e)
                continue

        if not strike_gex:
            return None

        sorted_strikes = sorted(strike_gex.keys())
        gex_values = [strike_gex[k] for k in sorted_strikes]
        gex_arr = np.array(gex_values)
        net_gex = float(np.sum(gex_arr))

        call_candidates = {k: v for k, v in call_gex_by_strike.items() if k >= spot}
        call_wall = max(call_candidates, key=call_candidates.get) if call_candidates else spot * 1.02

        put_candidates = {k: v for k, v in put_gex_by_strike.items() if k <= spot}
        put_wall = max(put_candidates, key=put_candidates.get) if put_candidates else spot * 0.98

        # Zero Gamma — find sign change in GEX profile across price scenarios
        price_range = np.linspace(spot * 0.90, spot * 1.10, 50)
        total_gex_at_price = []

        for price_scenario in price_range:
            scenario_gex = 0.0
            for exp in expirations[:2]:
                exp_date = date.fromisoformat(exp)
                T = max((exp_date - today).days / 365, 1 / 365)
                try:
                    chain = stock.option_chain(exp)
                    for _, row in chain.calls.iterrows():
                        K = float(row.get("strike", 0))
                        oi = int(row.get("openInterest", 0) or 0)
                        iv = float(row.get("impliedVolatility", 0.3) or 0.3)
                        if K <= 0 or oi == 0:
                            continue
                        scenario_gex += _black_scholes_gamma(price_scenario, K, T, r, iv) * oi * 100 * (price_scenario ** 2) * 0.01
                    for _, row in chain.puts.iterrows():
                        K = float(row.get("strike", 0))
                        oi = int(row.get("openInterest", 0) or 0)
                        iv = float(row.get("impliedVolatility", 0.3) or 0.3)
                        if K <= 0 or oi == 0:
                            continue
                        scenario_gex -= _black_scholes_gamma(price_scenario, K, T, r, iv) * oi * 100 * (price_scenario ** 2) * 0.01
                except Exception:
                    continue
            total_gex_at_price.append(scenario_gex / 1e9)

        zero_gamma = spot
        gex_at_prices = np.array(total_gex_at_price)
        for i in range(len(gex_at_prices) - 1):
            if gex_at_prices[i] * gex_at_prices[i + 1] < 0:
                zero_gamma = float(
                    price_range[i] +
                    (price_range[i + 1] - price_range[i]) *
                    abs(gex_at_prices[i]) /
                    (abs(gex_at_prices[i]) + abs(gex_at_prices[i + 1]))
                )
                break

        zero_gamma = round(zero_gamma, 2)
        vol_trigger = round((zero_gamma + put_wall) / 2, 2)
        gamma_regime = "POSITIVE" if spot > zero_gamma else "NEGATIVE"

        dist_call = round((call_wall / spot - 1) * 100, 2)
        dist_put = round((put_wall / spot - 1) * 100, 2)
        dist_zero = round((zero_gamma / spot - 1) * 100, 2)

        if gamma_regime == "POSITIVE":
            regime_note = (
                f"שוק ב-Positive Gamma — Market Makers מייצבים את השוק.\n"
                f"כשSPY עולה הם מוכרים, כשיורד הם קונים → תנועות מתונות."
            )
            interpretation = (
                f"📊 {symbol} מעל Zero Gamma (${zero_gamma}) → סביבה מייצבת.\n"
                f"Call Wall (תקרה): ${call_wall} ({dist_call:+.1f}%)\n"
                f"Put Wall (תמיכה): ${put_wall} ({dist_put:+.1f}%)\n"
                f"סביר להישאר בטווח ${put_wall}–${call_wall} לטווח הקצר."
            )
            strategy_implication = (
                "✅ סביבה מתאימה למכירת פרמיה:\n"
                "• Iron Condor עם strikes מחוץ לטווח Put Wall–Call Wall\n"
                "• Bull Put Spread ליד ה-Put Wall\n"
                "• 0DTE Credit Spreads בין הרמות"
            )
        else:
            regime_note = (
                f"שוק ב-Negative Gamma — Market Makers מאיצים תנועות!\n"
                f"כש{symbol} יורד הם מוכרים עוד, כשעולה הם קונים עוד → תנועות חדות."
            )
            interpretation = (
                f"⚠️ {symbol} מתחת ל-Zero Gamma (${zero_gamma}) → סביבה תנודתית!\n"
                f"Volatility Trigger: ${vol_trigger} — כניסה מעל מציבה יציבות\n"
                f"Call Wall: ${call_wall} | Put Wall: ${put_wall}\n"
                f"ירידה מתחת ל-${put_wall} עלולה להאיץ."
            )
            strategy_implication = (
                "⚠️ סביבה לא מתאימה למכירת פרמיה:\n"
                "• הימנע מ-Iron Condor ו-Short Strangle\n"
                "• שקול Long Puts / Protective Puts\n"
                "• הקטן פוזיציות ב-50% לפחות\n"
                "• המתן לחזרה מעל Volatility Trigger לפני כניסה חדשה"
            )

        result = GEXResult(
            symbol=symbol,
            spot_price=round(spot, 2),
            calculation_time=date.today().strftime("%d/%m/%Y"),
            zero_gamma=zero_gamma,
            call_wall=round(call_wall, 2),
            put_wall=round(put_wall, 2),
            vol_trigger=vol_trigger,
            net_gex=round(net_gex, 3),
            gamma_regime=gamma_regime,
            regime_note=regime_note,
            dist_to_call_wall=dist_call,
            dist_to_put_wall=dist_put,
            dist_to_zero_gamma=dist_zero,
            strikes=sorted_strikes,
            gex_profile=gex_values,
            interpretation=interpretation,
            strategy_implication=strategy_implication,
        )

        _cache[f"gex_{symbol}"] = (result, time.time())
        logger.info(
            "GEX %s: spot=%.2f zero_gamma=%.2f call_wall=%.2f put_wall=%.2f regime=%s",
            symbol, spot, zero_gamma, call_wall, put_wall, gamma_regime,
        )
        return result

    except Exception as e:
        logger.error("GEX calculation failed for %s: %s", symbol, e)
        return None


def format_gex_hebrew(g: GEXResult) -> str:
    """Format GEX result for Telegram."""
    regime_emoji = "🟢" if g.gamma_regime == "POSITIVE" else "🔴"
    net_sign = "+" if g.net_gex >= 0 else ""

    return (
        f"📊 *GEX Analysis — {g.symbol}*\n"
        f"🕙 {g.calculation_time} | מחיר: `${g.spot_price}`\n"
        f"{'━'*30}\n\n"

        f"{regime_emoji} *Gamma Regime: {g.gamma_regime}*\n"
        f"{g.regime_note}\n\n"

        f"🎯 *רמות מפתח:*\n"
        f"• 🔴 Call Wall (תקרה): `${g.call_wall}` ({g.dist_to_call_wall:+.1f}%)\n"
        f"• ⚡ Zero Gamma (פליפ): `${g.zero_gamma}` ({g.dist_to_zero_gamma:+.1f}%)\n"
        f"• ⚠️ Vol Trigger: `${g.vol_trigger}`\n"
        f"• 🟢 Put Wall (תמיכה): `${g.put_wall}` ({g.dist_to_put_wall:+.1f}%)\n"
        f"• Net GEX: `${net_sign}{g.net_gex:.2f}B`\n\n"

        f"💡 *פרשנות:*\n{g.interpretation}\n\n"

        f"{'━'*30}\n"
        f"🎯 *השלכה אסטרטגית:*\n{g.strategy_implication}"
    )
