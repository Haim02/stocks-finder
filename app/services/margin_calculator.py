"""
Margin requirement and capital efficiency calculator for options strategies.

Rules:
  Bull Put Spread  : Margin = (Width − Credit) × 100
  Bear Call Spread : Margin = (Width − Credit) × 100
  Iron Condor      : Margin = (Max(PutWing, CallWing) − TotalCredit) × 100
  Cash-Secured Put : Margin = Strike × 100
  Covered Call     : Margin = Price × 100 (stock cost)
  Debit Spreads    : Margin = Net Debit × 100
  Other            : Margin = Max Loss (if defined)
"""
import logging

logger = logging.getLogger(__name__)


def calculate_margin(signal) -> dict:
    """
    Return margin_required, return_on_capital, capital_efficiency label, and margin_note
    for the given StrategySignal.

    Returns dict with keys: margin, roc, label, note.
    """
    n      = signal.strategy_name
    mp     = signal.max_profit
    margin = 0.0
    note   = ""

    try:
        if n == "bull_put_spread":
            width  = signal.leg1_strike - signal.leg2_strike
            margin = (width - signal.net_credit) * 100
            note   = f"בטוחה = רוחב ספרד − קרדיט = ${width:.0f} − ${signal.net_credit} = ${margin:.0f}"

        elif n == "bear_call_spread":
            width  = signal.leg2_strike - signal.leg1_strike
            margin = (width - signal.net_credit) * 100
            note   = f"בטוחה = רוחב ספרד − קרדיט = ${width:.0f} − ${signal.net_credit} = ${margin:.0f}"

        elif n == "iron_condor":
            put_wing  = signal.leg1_strike - signal.leg2_strike
            call_wing = signal.leg4_strike - signal.leg3_strike
            margin    = (max(put_wing, call_wing) - signal.net_credit) * 100
            note      = f"בטוחה = Max(Put, Call כנף) − קרדיט = ${margin:.0f}"

        elif n == "cash_secured_put":
            margin = signal.leg1_strike * 100
            note   = f"בטוחה = ערך מלא של הפוט = ${margin:.0f} (לרכישה ב-${signal.leg1_strike})"

        elif n == "covered_call":
            margin = signal.underlying_price * 100
            note   = f"בטוחה = ערך מלא של 100 מניות = ${margin:.0f}"

        elif n in ("bull_call_spread", "bear_put_spread", "calendar_spread", "butterfly",
                   "broken_wing_butterfly"):
            margin = signal.net_debit * 100
            note   = f"בטוחה = דביט נטו = ${margin:.0f}"

        elif n in ("long_straddle", "long_call_leap"):
            margin = signal.net_debit * 100
            note   = f"בטוחה = פרמיה ששולמה = ${margin:.0f}"

        elif n == "call_back_ratio":
            margin = max(signal.max_loss, signal.net_debit * 100)
            note   = f"בטוחה = הפסד מקסימלי = ${margin:.0f}"

        else:
            margin = signal.max_loss if signal.max_loss < 9_999_990 else 0.0
            note   = f"בטוחה = הפסד מקסימלי = ${margin:.0f}"

        margin = round(max(margin, 0.0), 2)

        # ROC = max_profit / margin * 100
        if margin > 0 and mp < 9_999_990:
            roc = round((mp / margin) * 100, 2)
        else:
            roc = 0.0

        # Efficiency label
        if roc >= 15:
            label = "🟢 מצוין"
        elif roc >= 8:
            label = "🟡 טוב"
        elif roc >= 4:
            label = "🟠 בינוני"
        else:
            label = "🔴 נמוך"

        return {"margin": margin, "roc": roc, "label": label, "note": note}

    except Exception as e:
        logger.debug("calculate_margin failed for %s/%s: %s", signal.ticker, signal.strategy_name, e)
        return {"margin": 0.0, "roc": 0.0, "label": "—", "note": ""}
