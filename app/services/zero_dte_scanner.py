"""
zero_dte_scanner.py — 0DTE Options Scanner
==========================================

Analyzes 0DTE (Zero Days To Expiration) options opportunities.
Based on concepts from alpacahq/gamma-scalping.

Key features:
- Calculate today's expected move (daily EM)
- Find 0DTE strikes outside the EM
- Assess VIX-based sizing and timing
- Calculate Gamma exposure for risk management

Best used: 10:00-11:00 AM ET (17:00-18:00 Israel time)
"""

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

# 0DTE symbols available every trading day
ZERO_DTE_SYMBOLS = ["SPY", "QQQ"]
# Weekly 0DTE (check which day of week)
WEEKLY_ZERO_DTE = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"]


@dataclass
class ZeroDTESetup:
    symbol: str
    current_price: float
    vix: float
    daily_em: float          # ±$ expected move for today
    daily_em_pct: float      # % expected move

    # Recommended setup
    strategy: str            # "Iron Condor" | "Bull Put Spread" | "Bear Call Spread" | "Skip"
    put_strike: float        # short put strike (below EM)
    call_strike: float       # short call strike (above EM)
    expiration: str          # today's date

    # Risk metrics
    sizing_note: str         # position size recommendation
    timing_note: str         # when to enter
    risk_level: str          # "LOW" | "MEDIUM" | "HIGH" | "SKIP"

    # Greeks at short strikes
    put_delta: float
    call_delta: float
    gamma_risk: str          # "LOW" | "HIGH" — warning if Gamma is extreme


def _get_vix() -> float:
    """Fetch current VIX level."""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
        return 20.0
    except Exception:
        return 20.0


def _get_daily_em(symbol: str, price: float, iv: float) -> float:
    """
    Calculate daily expected move.
    Formula: Price × IV × √(1/252)
    iv is decimal (0.25 = 25%)
    """
    if price <= 0 or iv <= 0:
        return 0.0
    daily_em = price * iv * math.sqrt(1 / 252)
    return round(daily_em, 2)


def _assess_timing_and_sizing(vix: float) -> tuple[str, str, str, str]:
    """
    Returns (strategy, sizing_note, timing_note, risk_level) based on VIX.
    This is the core 0DTE decision matrix.
    """
    israel_now = datetime.now()
    hour = israel_now.hour
    minute = israel_now.minute
    time_decimal = hour + minute / 60

    # Israel time → ET: Israel is UTC+3, ET is UTC-4 → Israel = ET + 7
    # So ET hour = Israel hour - 7
    et_hour = time_decimal - 7
    if et_hour < 0:
        et_hour += 24

    # VIX-based risk assessment
    if vix > 28:
        return "Skip", "אל תסחר 0DTE היום — VIX גבוה מדי", "המתן לחודשי", "SKIP"
    elif vix > 22:
        risk = "HIGH"
        sizing = "סיזינג: 0.5-1% מהחשבון (VIX גבוה — זהירות)"
    elif vix > 18:
        risk = "MEDIUM"
        sizing = "סיזינג: 1-1.5% מהחשבון"
    else:
        risk = "LOW"
        sizing = "סיזינג: 1.5-2% מהחשבון (VIX תקין)"

    # Time-based guidance
    if et_hour < 10.0:
        timing = "⚠️ מוקדם מדי — המתן עד 10:00 AM ET (17:00 ישראל)"
        strategy = "Wait"
    elif et_hour < 11.0:
        timing = "✅ חלון כניסה מומלץ (10:00-11:00 AM ET)"
        strategy = "Iron Condor" if vix < 18 else "Bull Put Spread"
    elif et_hour < 13.0:
        timing = "✅ כניסה אפשרית — Iron Condor אידאלי"
        strategy = "Iron Condor"
    elif et_hour < 14.5:
        timing = "⚠️ Theta מתחיל לחץ — כניסה מוגבלת"
        strategy = "Skip"
    else:
        timing = "🔴 מאוחר מדי — אל תיכנס לפוזיציות חדשות"
        strategy = "Skip"

    if vix > 22 and strategy not in ("Skip", "Wait"):
        timing += f" | VIX={vix:.1f} — הכנס רק אחרי 11:00 AM ET"

    return strategy, sizing, timing, risk


def _calc_delta_approx(price: float, strike: float, iv: float, option_type: str) -> float:
    """Approximate delta for 0DTE using Black-Scholes (T very small)."""
    try:
        from app.options_engine.greeks import calculate_greeks
        T = 1 / 365  # 0DTE = 1 day
        g = calculate_greeks(price, strike, T, iv, option_type)
        return g.delta
    except Exception:
        # Very rough approximation
        distance = abs(price - strike) / price
        base = 0.5 * math.exp(-distance * 10)
        return -base if option_type == "put" else base


def analyze_zero_dte(symbol: str = "SPY") -> Optional[ZeroDTESetup]:
    """
    Full 0DTE analysis for a symbol.
    Returns setup recommendation or None if conditions not met.
    """
    try:
        from app.services.realtime_market_data import get_realtime_iv_data

        # Get price and IV
        iv_data = get_realtime_iv_data(symbol)
        if iv_data.current_price <= 0:
            logger.warning("Could not get price for %s", symbol)
            return None

        price = iv_data.current_price
        iv = iv_data.iv_current / 100  # convert to decimal
        if iv <= 0:
            iv = 0.20  # default 20% IV

        # Get VIX
        vix = _get_vix()

        # Calculate daily expected move
        daily_em = _get_daily_em(symbol, price, iv)
        daily_em_pct = round(daily_em / price * 100, 2)

        # Get timing and sizing recommendation
        strategy, sizing, timing, risk = _assess_timing_and_sizing(vix)

        if strategy in ("Skip", "Wait") or risk == "SKIP":
            return ZeroDTESetup(
                symbol=symbol,
                current_price=price,
                vix=vix,
                daily_em=daily_em,
                daily_em_pct=daily_em_pct,
                strategy=strategy,
                put_strike=0.0,
                call_strike=0.0,
                expiration=date.today().isoformat(),
                sizing_note=sizing,
                timing_note=timing,
                risk_level=risk,
                put_delta=0.0,
                call_delta=0.0,
                gamma_risk="HIGH",
            )

        # Place strikes OUTSIDE the expected move (1.1× cushion)
        cushion = 1.1
        put_strike = round(price - daily_em * cushion, 0)
        call_strike = round(price + daily_em * cushion, 0)

        # Calculate deltas
        put_delta = _calc_delta_approx(price, put_strike, iv, "put")
        call_delta = _calc_delta_approx(price, call_strike, iv, "call")

        # Gamma risk assessment (0DTE gamma is always high near expiration)
        distance_pct = min(
            abs(price - put_strike) / price,
            abs(price - call_strike) / price
        ) * 100
        gamma_risk = "HIGH" if distance_pct < 1.5 else "LOW"

        logger.info(
            "0DTE %s: price=$%.2f VIX=%.1f EM=±$%.2f (%.2f%%) "
            "Put=$%.0f Call=$%.0f strategy=%s",
            symbol, price, vix, daily_em, daily_em_pct,
            put_strike, call_strike, strategy
        )

        return ZeroDTESetup(
            symbol=symbol,
            current_price=price,
            vix=vix,
            daily_em=daily_em,
            daily_em_pct=daily_em_pct,
            strategy=strategy,
            put_strike=put_strike,
            call_strike=call_strike,
            expiration=date.today().isoformat(),
            sizing_note=sizing,
            timing_note=timing,
            risk_level=risk,
            put_delta=round(put_delta, 3),
            call_delta=round(call_delta, 3),
            gamma_risk=gamma_risk,
        )

    except Exception as e:
        logger.error("0DTE analysis failed for %s: %s", symbol, e)
        return None


def format_zero_dte_report(setup: ZeroDTESetup) -> str:
    """Format 0DTE setup as Hebrew Telegram message."""
    if not setup:
        return "⚠️ לא הצלחתי לנתח 0DTE כרגע."

    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "SKIP": "⛔"}.get(
        setup.risk_level, "⚪"
    )

    if setup.strategy in ("Skip", "Wait"):
        return (
            f"📅 *0DTE Analysis — {setup.symbol}*\n\n"
            f"{risk_emoji} סטטוס: *{setup.strategy}*\n"
            f"VIX: `{setup.vix}` | מחיר: `${setup.current_price}`\n\n"
            f"⏰ {setup.timing_note}\n\n"
            f"📐 Expected Move יומי: `±${setup.daily_em}` ({setup.daily_em_pct}%)"
        )

    gamma_warn = "\n⚠️ *Gamma Risk גבוה — עקוב מקרוב!*" if setup.gamma_risk == "HIGH" else ""

    return (
        f"📅 *0DTE Analysis — {setup.symbol}*\n"
        f"{'━' * 28}\n\n"
        f"{risk_emoji} רמת סיכון: *{setup.risk_level}* | VIX: `{setup.vix}`\n"
        f"💰 מחיר נוכחי: `${setup.current_price}`\n"
        f"📐 Expected Move יומי: `±${setup.daily_em}` ({setup.daily_em_pct}%)\n\n"
        f"🎯 *אסטרטגיה מומלצת: {setup.strategy}*\n"
        f"• Put Strike (מכור): `${setup.put_strike}` (Delta: `{setup.put_delta:.3f}`)\n"
        f"• Call Strike (מכור): `${setup.call_strike}` (Delta: `{setup.call_delta:.3f}`)\n"
        f"• פקיעה: `{setup.expiration}` (היום!)\n\n"
        f"⏰ *תזמון:* {setup.timing_note}\n"
        f"📦 {setup.sizing_note}{gamma_warn}\n\n"
        f"{'━' * 28}\n"
        f"🔴 *כללי ברזל ל-0DTE:*\n"
        f"• סגור ב-50% רווח מיידית\n"
        f"• צא ב-150% הפסד — אל תחכה\n"
        f"• סגור הכל לפני 22:00 שעון ישראל\n"
        f"• אל תחזיק לפקיעה!"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for sym in ["SPY", "QQQ"]:
        setup = analyze_zero_dte(sym)
        if setup:
            print(f"\n{format_zero_dte_report(setup)}")
