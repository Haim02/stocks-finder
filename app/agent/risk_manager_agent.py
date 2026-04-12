"""
risk_manager_agent.py — Agent 3: Risk Manager
===============================================

Monitors open options positions and sends proactive Telegram alerts
when Tastytrade management rules are triggered.

Runs every hour during market hours: 09:30–16:30 Israel time (Mon–Fri).

Position Lifecycle:
  Haim opens a trade → logs it via /addposition in Telegram
  Agent 3 monitors every hour → alerts on triggers
  Haim closes trade → marks it via /closeposition in Telegram

Alert Rules (Tastytrade methodology):
  ✅ 50% profit  → "סגור עכשיו — הגעת ליעד"
  ⚠️ 21 DTE     → "זמן לבדוק את הפוזיציה"
  🔴 2× credit  → "STOP LOSS — צא מיד"
  📅 10 DTE     → "סגור הכל — גאמא מסוכן מדי"

MongoDB collection: open_positions
  {
    ticker: str,
    strategy: str,
    short_strike: float,
    long_strike: float,
    credit_received: float,   # net credit per share when opened
    spread_width: float,
    dte_at_open: int,
    expiration_date: str,     # YYYY-MM-DD
    contracts: int,
    opened_at: datetime,
    status: "open" | "closed" | "alerted_50pct" | "alerted_21dte" | "alerted_10dte",
    last_checked: datetime,
    close_price: float | None,
    notes: str,
  }
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

# ── Alert thresholds (Tastytrade rules) ───────────────────────────────────────
PROFIT_TARGET_PCT  = 0.50   # close at 50% of credit
STOP_LOSS_MULT     = 2.0    # exit at 2× original credit
REVIEW_DTE         = 21     # review at 21 DTE
HARD_EXIT_DTE      = 10     # close everything at 10 DTE


# ── Price fetcher ─────────────────────────────────────────────────────────────

def _get_option_mid_price(
    ticker: str,
    expiration: str,
    strike: float,
    option_type: str,   # "call" or "put"
) -> Optional[float]:
    """
    Fetch current mid-price (bid+ask)/2 for a specific option contract.
    Returns None on failure.
    """
    try:
        stock = yf.Ticker(ticker)
        chain = stock.option_chain(expiration)
        df = chain.calls if option_type == "call" else chain.puts

        row = df[df["strike"] == strike]
        if row.empty:
            # Find closest strike
            df = df.copy()
            df["distance"] = abs(df["strike"] - strike)
            row = df.nsmallest(1, "distance")

        if row.empty:
            return None

        bid = float(row.iloc[0].get("bid", 0) or 0)
        ask = float(row.iloc[0].get("ask", 0) or 0)
        if ask == 0:
            return None
        return round((bid + ask) / 2, 2)

    except Exception as e:
        logger.warning("Option price fetch failed %s %s %s: %s", ticker, strike, option_type, e)
        return None


def _estimate_current_spread_cost(position: dict) -> Optional[float]:
    """
    Estimate what it would cost NOW to buy back the spread (close the position).
    For Bull Put Spread: cost = short_put_price - long_put_price
    Returns None if prices unavailable.
    """
    try:
        ticker      = position["ticker"]
        expiration  = position["expiration_date"]
        short_k     = float(position["short_strike"])
        long_k      = float(position["long_strike"])
        strategy    = position.get("strategy", "")

        if "Put" in strategy or strategy == "Bull Put Spread":
            opt_type = "put"
        elif "Call" in strategy or strategy == "Bear Call Spread":
            opt_type = "call"
        else:
            opt_type = "put"  # default to put side for condor

        short_price = _get_option_mid_price(ticker, expiration, short_k, opt_type)
        long_price  = _get_option_mid_price(ticker, expiration, long_k, opt_type)

        if short_price is None or long_price is None:
            return None

        # Current cost to close = what we pay to buy back short - what we get selling long
        return round(short_price - long_price, 2)

    except Exception as e:
        logger.warning("Spread cost estimation failed: %s", e)
        return None


def _calc_dte(expiration_date_str: str) -> int:
    """Calculate days to expiration from today."""
    try:
        exp = date.fromisoformat(expiration_date_str)
        return max(0, (exp - date.today()).days)
    except Exception:
        return 999


# ── Alert builders ────────────────────────────────────────────────────────────

def _build_profit_alert(pos: dict, current_cost: float, profit_pct: float) -> str:
    credit = float(pos["credit_received"])
    contracts = int(pos.get("contracts", 1))
    profit_per_contract = round((credit - current_cost) * 100, 2)
    total_profit = round(profit_per_contract * contracts, 2)

    return (
        f"✅ *יעד רווח הושג!*\n\n"
        f"📌 {pos['ticker']} — {pos['strategy']}\n"
        f"💰 קרדיט שקיבלת: `${credit}` לצמד\n"
        f"💸 עלות סגירה כעת: `${current_cost}` לצמד\n"
        f"📈 רווח: `{round(profit_pct * 100, 1)}%` מהקרדיט\n"
        f"💵 רווח כולל: `${total_profit}` ({contracts} חוזים)\n\n"
        f"🎯 *הכלל: סגור ב-50% — הגיע הזמן!*\n"
        f"השאר חצי שני לא שווה את הסיכון."
    )


def _build_stop_loss_alert(pos: dict, current_cost: float, loss_mult: float) -> str:
    credit = float(pos["credit_received"])
    contracts = int(pos.get("contracts", 1))
    loss_per_contract = round((current_cost - credit) * 100, 2)
    total_loss = round(loss_per_contract * contracts, 2)

    return (
        f"🔴 *STOP LOSS — צא מיד!*\n\n"
        f"📌 {pos['ticker']} — {pos['strategy']}\n"
        f"💰 קרדיט שקיבלת: `${credit}` לצמד\n"
        f"💸 עלות סגירה כעת: `${current_cost}` לצמד\n"
        f"📉 ההפסד הגיע ל-`{round(loss_mult, 1)}×` הקרדיט\n"
        f"💸 הפסד כולל: `${total_loss}` ({contracts} חוזים)\n\n"
        f"⛔ *הכלל: צא ב-2× קרדיט — ללא יוצא מהכלל!*\n"
        f"אל תחכה לריבאונד. הפסד קטן עכשיו עדיף על הפסד גדול מאוחר יותר."
    )


def _build_dte_alert(pos: dict, dte: int) -> str:
    if dte <= HARD_EXIT_DTE:
        emoji = "📅"
        title = f"סגור הכל — {dte} ימים לפקיעה!"
        body = (
            f"⚠️ *גאמא מסוכן מדי* — בשבועיים האחרונים לפני פקיעה\n"
            f"הפוזיציה יכולה להתהפך במהירות.\n"
            f"*סגור עכשיו, ללא יוצא מהכלל.*"
        )
    else:
        emoji = "⚠️"
        title = f"בדוק את הפוזיציה — {dte} ימים לפקיעה"
        body = (
            f"הגעת ל-21 DTE — זמן לקבל החלטה:\n"
            f"• אם ברווח → שקול לסגור עכשיו\n"
            f"• אם בהפסד → החלט עכשיו, לא תחת לחץ\n"
            f"• אל תישאר ב-drift — קבל החלטה מודעת"
        )

    return (
        f"{emoji} *{title}*\n\n"
        f"📌 {pos['ticker']} — {pos['strategy']}\n"
        f"📅 פקיעה: `{pos['expiration_date']}`\n"
        f"⏰ ימים שנותרו: `{dte}`\n\n"
        f"{body}"
    )


# ── Main Agent ────────────────────────────────────────────────────────────────

class RiskManagerAgent:
    """
    Agent 3 — Risk Manager.

    Runs every hour. Checks all open positions in MongoDB.
    Sends Telegram alerts when management rules are triggered.

    Usage:
        agent = RiskManagerAgent()
        agent.run()
    """

    def __init__(self):
        from app.data.mongo_client import MongoDB
        self._db = MongoDB.get_db()
        self._collection = self._db["open_positions"]

    def run(self) -> dict:
        logger.info("=== Agent 3: Risk Manager — START ===")

        positions = self._get_open_positions()
        if not positions:
            logger.info("No open positions to monitor.")
            return {"checked": 0, "alerts_sent": 0}

        logger.info("Monitoring %d open position(s)...", len(positions))
        alerts_sent = 0

        for pos in positions:
            ticker = pos.get("ticker", "?")
            try:
                alerts = self._check_position(pos)
                for alert_msg in alerts:
                    self._send_alert(alert_msg)
                    alerts_sent += 1
                self._update_last_checked(pos["_id"])
            except Exception as e:
                logger.error("Error checking position %s: %s", ticker, e)

        logger.info(
            "=== Agent 3: Risk Manager — DONE | %d positions checked, %d alerts sent ===",
            len(positions), alerts_sent,
        )
        return {"checked": len(positions), "alerts_sent": alerts_sent}

    def _get_open_positions(self) -> list[dict]:
        try:
            return list(self._collection.find(
                {"status": {"$in": ["open", "alerted_50pct", "alerted_21dte"]}}
            ))
        except Exception as e:
            logger.error("Failed to fetch open positions: %s", e)
            return []

    def _check_position(self, pos: dict) -> list[str]:
        """Check a single position against all alert rules. Returns list of alert messages."""
        alerts = []
        ticker = pos.get("ticker", "?")
        credit = float(pos.get("credit_received", 0))
        status = pos.get("status", "open")

        # 1. Calculate DTE
        dte = _calc_dte(pos.get("expiration_date", ""))

        # 2. Hard exit at 10 DTE (highest priority)
        if dte <= HARD_EXIT_DTE and status != "alerted_10dte":
            alerts.append(_build_dte_alert(pos, dte))
            self._update_status(pos["_id"], "alerted_10dte")
            logger.warning("ALERT: %s at %d DTE — hard exit", ticker, dte)
            return alerts  # no further checks needed

        # 3. 21 DTE review
        if dte <= REVIEW_DTE and status == "open":
            alerts.append(_build_dte_alert(pos, dte))
            self._update_status(pos["_id"], "alerted_21dte")
            logger.info("ALERT: %s at %d DTE — review", ticker, dte)

        # 4. Get current spread cost
        current_cost = _estimate_current_spread_cost(pos)
        if current_cost is None:
            logger.info("Could not get current price for %s — skipping P&L check", ticker)
            return alerts

        if credit <= 0:
            return alerts

        # 5. Check 50% profit target
        profit_pct = (credit - current_cost) / credit
        if profit_pct >= PROFIT_TARGET_PCT and status not in ("alerted_50pct", "alerted_10dte"):
            alerts.append(_build_profit_alert(pos, current_cost, profit_pct))
            self._update_status(pos["_id"], "alerted_50pct")
            logger.info("ALERT: %s hit 50%% profit (%.1f%%)", ticker, profit_pct * 100)

        # 6. Check stop loss (2× credit)
        loss_mult = current_cost / credit if credit > 0 else 0
        if loss_mult >= STOP_LOSS_MULT:
            alerts.append(_build_stop_loss_alert(pos, current_cost, loss_mult))
            self._update_status(pos["_id"], "stop_loss_hit")
            logger.warning("ALERT: %s hit STOP LOSS (%.1fx credit)", ticker, loss_mult)

        return alerts

    def _send_alert(self, message: str) -> None:
        try:
            from app.agent.telegram_bot import notify_trade
            notify_trade(message)
        except Exception as e:
            logger.error("Failed to send Telegram alert: %s", e)

    def _update_status(self, position_id, new_status: str) -> None:
        try:
            self._collection.update_one(
                {"_id": position_id},
                {"$set": {"status": new_status, "last_alerted": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error("Failed to update position status: %s", e)

    def _update_last_checked(self, position_id) -> None:
        try:
            self._collection.update_one(
                {"_id": position_id},
                {"$set": {"last_checked": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error("Failed to update last_checked: %s", e)

    # ── Position management helpers ───────────────────────────────────────────

    @staticmethod
    def add_position(
        ticker: str,
        strategy: str,
        short_strike: float,
        long_strike: float,
        credit_received: float,
        spread_width: float,
        expiration_date: str,
        contracts: int = 1,
        notes: str = "",
    ) -> bool:
        """
        Add a new open position to MongoDB.
        Called by /addposition Telegram command.
        """
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            exp = date.fromisoformat(expiration_date)
            dte_at_open = (exp - date.today()).days

            doc = {
                "ticker": ticker.upper(),
                "strategy": strategy,
                "short_strike": short_strike,
                "long_strike": long_strike,
                "credit_received": credit_received,
                "spread_width": spread_width,
                "dte_at_open": dte_at_open,
                "expiration_date": expiration_date,
                "contracts": contracts,
                "opened_at": datetime.utcnow(),
                "status": "open",
                "last_checked": datetime.utcnow(),
                "close_price": None,
                "notes": notes,
            }
            db["open_positions"].insert_one(doc)
            logger.info("Position added: %s %s exp=%s", ticker, strategy, expiration_date)
            return True
        except Exception as e:
            logger.error("Failed to add position: %s", e)
            return False

    @staticmethod
    def close_position(ticker: str, close_price: float) -> bool:
        """
        Mark a position as closed.
        Called by /closeposition Telegram command.
        """
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            result = db["open_positions"].update_one(
                {"ticker": ticker.upper(), "status": {"$ne": "closed"}},
                {"$set": {
                    "status": "closed",
                    "close_price": close_price,
                    "closed_at": datetime.utcnow(),
                }},
                sort=[("opened_at", -1)],
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error("Failed to close position: %s", e)
            return False

    @staticmethod
    def get_open_positions_summary() -> str:
        """Returns a Hebrew summary of all open positions for /positions command."""
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            positions = list(db["open_positions"].find(
                {"status": {"$nin": ["closed"]}},
                sort=[("opened_at", -1)],
            ))

            if not positions:
                return "📭 *אין פוזיציות פתוחות כרגע.*\n\nהוסף פוזיציה עם /addposition"

            lines = [f"📋 *פוזיציות פתוחות ({len(positions)}):*\n"]
            for p in positions:
                dte = _calc_dte(p.get("expiration_date", ""))
                dte_warn = " ⚠️" if dte <= 21 else ""
                lines.append(
                    f"• *{p['ticker']}* — {p['strategy']}\n"
                    f"  Credit: `${p['credit_received']}` | "
                    f"Exp: `{p['expiration_date']}` ({dte} DTE){dte_warn}\n"
                    f"  Status: `{p['status']}`"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error("Failed to get positions summary: %s", e)
            return "⚠️ שגיאה בשליפת הפוזיציות."


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    agent = RiskManagerAgent()
    result = agent.run()
    print(f"\nDone: {result}")
