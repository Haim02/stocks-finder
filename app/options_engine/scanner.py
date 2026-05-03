"""
scanner.py — Main Entry Point
"""
import logging
from app.options_engine.iv import get_iv, SYMBOLS
from app.options_engine.strategies import select_strategies, build_setup
from app.options_engine.alerts import check_and_alert

logger = logging.getLogger(__name__)


def run_options_engine(symbols: list[str] = None) -> list[dict]:
    symbols = symbols or SYMBOLS
    logger.info("=== Options Engine — %d symbols ===", len(symbols))
    all_setups = []

    for symbol in symbols:
        iv_result = get_iv(symbol)
        if not iv_result:
            logger.warning("Skip %s — no IV data", symbol)
            continue

        strategies = select_strategies(iv_result.iv_rank)
        logger.info("%s IV Rank=%.2f → %s", symbol, iv_result.iv_rank, strategies[0])

        for strategy in strategies[:1]:
            setup = build_setup(symbol, iv_result.price, iv_result.iv_current,
                               iv_result.iv_rank, strategy)
            if setup:
                all_setups.append(setup)
                break

    if all_setups:
        check_and_alert(all_setups)

    return [
        {"symbol": s.symbol, "price": s.price, "iv": s.iv, "iv_rank": s.iv_rank,
         "strategy": s.strategy, "expiration": s.expiration, "dte": s.dte,
         "strikes": s.strikes, "greeks": s.greeks, "credit": s.credit,
         "max_loss": s.max_loss, "probability_profit": s.probability_profit,
         "return_on_risk": s.return_on_risk}
        for s in all_setups
    ]


def _get_ror(r: dict) -> float:
    try:
        return float(r.get("return_on_risk", 0))
    except Exception:
        return 0.0


def _format_single_opportunity(r: dict) -> str:
    try:
        ticker = r.get("symbol", "")
        strategy = r.get("strategy", "")
        price = r.get("price", 0)
        iv_rank = r.get("iv_rank", 0) * 100   # stored as 0-1
        expiration = r.get("expiration", "")
        dte = r.get("dte", 0)
        credit = abs(float(r.get("credit", 0) or 0))
        max_loss = abs(float(r.get("max_loss", 0) or 0))
        ror = _get_ror(r)
        strikes = r.get("strikes", {})

        if "Iron Condor" in strategy:
            strikes_lines = (
                f"  🔴 מכור Call `${strikes.get('call_sell', 0):.0f}` | "
                f"🔵 קנה Call `${strikes.get('call_buy', 0):.0f}`\n"
                f"  🔴 מכור Put  `${strikes.get('put_sell', 0):.0f}` | "
                f"🔵 קנה Put  `${strikes.get('put_buy', 0):.0f}`"
            )
        elif "Put" in strategy:
            strikes_lines = (
                f"  🔴 מכור Put `${strikes.get('put_sell', 0):.0f}` | "
                f"🔵 קנה Put `${strikes.get('put_buy', 0):.0f}`"
            )
        elif "Call" in strategy:
            strikes_lines = (
                f"  🔴 מכור Call `${strikes.get('call_sell', 0):.0f}` | "
                f"🔵 קנה Call `${strikes.get('call_buy', 0):.0f}`"
            )
        else:
            strikes_lines = ""

        credit_line = (
            f"  💰 קרדיט: `${credit:.2f}` | הפסד מקסימלי: `${max_loss:.0f}`"
            if credit > 0 else ""
        )
        ror_emoji = "🟢" if ror >= 30 else "🟡" if ror >= 10 else "⚪"
        ror_line = f"  {ror_emoji} תשואה על סיכון: `{ror:.1f}%`" if ror > 0 else ""

        lines = [
            f"  *{ticker}* | `${float(price):.2f}` | IV Rank: `{iv_rank:.0f}%`",
            f"  📅 פקיעה: `{expiration}` ({dte} ימים)",
            f"  📋 *{strategy}*",
        ]
        if strikes_lines:
            lines.append(strikes_lines)
        if credit_line:
            lines.append(credit_line)
        if ror_line:
            lines.append(ror_line)
        lines.append("  ──────────────────────────")
        return "\n".join(lines)

    except Exception as e:
        return f"  ⚠️ שגיאה בעיצוב: {e}"


def format_scan_results_hebrew(results: list, scan_date: str = None) -> str:
    """Format options scan results as a beautiful Hebrew Telegram message."""
    from datetime import date as dt

    if not results:
        return "⚠️ לא נמצאו הזדמנויות כרגע. נסה שוב כשהשוק פתוח."

    today = scan_date or dt.today().strftime("%d/%m/%Y")

    lines = [
        f"📊 *סורק אופציות — {today}*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    excellent = [r for r in results if _get_ror(r) >= 30]
    good      = [r for r in results if 10 <= _get_ror(r) < 30]
    watch     = [r for r in results if _get_ror(r) < 10]

    if excellent:
        lines.append("\n🟢 *הזדמנויות מצוינות (RoR > 30%):*")
        for r in excellent[:3]:
            lines.append(_format_single_opportunity(r))

    if good:
        lines.append("\n🟡 *הזדמנויות טובות (RoR 10-30%):*")
        for r in good[:3]:
            lines.append(_format_single_opportunity(r))

    if watch and not excellent and not good:
        lines.append("\n📋 *לעקוב:*")
        for r in watch[:3]:
            lines.append(_format_single_opportunity(r))

    lines.append(
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *איך לקרוא:*\n"
        "🔴 = מכור (Sell) | 🔵 = קנה (Buy)\n"
        "RoR = תשואה על הסיכון | DTE = ימים לפקיעה"
    )

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_options_engine()
    for r in results:
        print(r)
