"""
alerts.py — Telegram Alert System
"""
import logging
from app.options_engine.strategies import StrategySetup

logger = logging.getLogger(__name__)


def check_and_alert(setups: list[StrategySetup]) -> None:
    if not setups:
        return
    high_iv = [s for s in setups if s.iv_rank > 0.7]
    _send_telegram(setups, high_iv)


def _send_telegram(setups: list[StrategySetup], high_iv: list[StrategySetup]) -> None:
    try:
        from app.agent.telegram_bot import notify_trade
        notify_trade(_build_message(setups, high_iv))
    except Exception as e:
        logger.error("Telegram alert failed: %s", e)


def _build_message(setups: list[StrategySetup], high_iv: list[StrategySetup]) -> str:
    lines = ["🔍 *Options Scanner — הזדמנויות יומיות*\n"]

    if high_iv:
        lines.append("🚨 *IV גבוה במיוחד (>70%):*")
        for s in high_iv:
            lines.append(f"• *{s.symbol}* — IV Rank: `{s.iv_rank*100:.0f}%` 🔥  {s.strategy}")
        lines.append("")

    lines.append("📊 *כל ההזדמנויות:*")
    for s in setups:
        iv_emoji = "🔥" if s.iv_rank > 0.6 else ("❄️" if s.iv_rank < 0.3 else "✅")
        strikes_str = " | ".join(f"{k}: ${v}" for k, v in s.strikes.items())
        lines.append(
            f"\n{iv_emoji} *{s.symbol}* — {s.strategy}\n"
            f"• מחיר: `${s.price}` | IV: `{s.iv}%` | Rank: `{s.iv_rank*100:.0f}%`\n"
            f"• פקיעה: `{s.expiration}` ({s.dte} DTE)\n"
            f"• Strikes: `{strikes_str}`\n"
            f"• Credit: `${s.credit}` | Max Loss: `${s.max_loss}` | RoR: `{s.return_on_risk}%`\n"
            f"• Delta: `{s.greeks.get('delta',0):.3f}` | "
            f"Theta: `{s.greeks.get('theta',0):.3f}` | "
            f"Vega: `{s.greeks.get('vega',0):.3f}`"
        )
    return "\n".join(lines)
