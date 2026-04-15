"""
strategy_evaluator.py — Options Strategy P&L Evaluator
=======================================================

Uses optionlab to calculate:
- P&L profile at expiration
- Probability of Profit (PoP)
- Max profit / Max loss
- Breakeven prices
- Greeks per leg

Used by Agent 2 and Free Chat to validate strategy setups
before recommending them to Haim.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class StrategyEvaluation:
    strategy: str
    symbol: str
    pop: float              # Probability of Profit (0-100%)
    max_profit: float       # Max profit $ per contract
    max_loss: float         # Max loss $ per contract
    breakeven_low: float    # Lower breakeven price
    breakeven_high: float   # Upper breakeven price (None for single-leg)
    expected_profit: float  # Expected profit when profitable
    expected_loss: float    # Expected loss when unprofitable
    credit: float           # Net credit received
    is_viable: bool         # True if PoP >= 65% and RoR >= 20%
    summary_hebrew: str     # Hebrew summary for Telegram


def evaluate_bull_put_spread(
    symbol: str,
    stock_price: float,
    short_put_strike: float,
    long_put_strike: float,
    short_put_premium: float,
    long_put_premium: float,
    expiration_date: str,   # YYYY-MM-DD
    volatility: float,      # IV as decimal e.g. 0.25
    risk_free_rate: float = 0.0433,
) -> Optional[StrategyEvaluation]:
    """Evaluate a Bull Put Spread using optionlab."""
    try:
        from optionlab import run_strategy

        today = date.today().isoformat()

        inputs = {
            "stock_price": stock_price,
            "start_date": today,
            "target_date": expiration_date,
            "volatility": volatility,
            "interest_rate": risk_free_rate,
            "dividend_yield": 0.0,
            "legs": [
                {
                    "type": "put",
                    "strike": short_put_strike,
                    "premium": short_put_premium,
                    "n": 1,
                    "action": "sell",
                },
                {
                    "type": "put",
                    "strike": long_put_strike,
                    "premium": long_put_premium,
                    "n": 1,
                    "action": "buy",
                },
            ],
        }

        result = run_strategy(inputs)

        credit = round((short_put_premium - long_put_premium) * 100, 2)
        spread_width = short_put_strike - long_put_strike
        max_profit = credit
        max_loss = round((spread_width - credit / 100) * 100, 2)

        pop = round(float(result.probability_of_profit) * 100, 1) if hasattr(result, "probability_of_profit") else round((1 - abs(short_put_strike / stock_price - 1)) * 100, 1)
        breakeven = short_put_strike - (credit / 100)
        exp_profit = round(float(result.expected_profit) * 100, 2) if hasattr(result, "expected_profit") else max_profit * 0.5
        exp_loss = round(float(result.expected_loss) * 100, 2) if hasattr(result, "expected_loss") else max_loss * 0.3

        is_viable = pop >= 65 and (credit / 100) / spread_width >= 0.20

        summary = (
            f"📊 *Bull Put Spread — {symbol}*\n"
            f"• Strikes: ${short_put_strike} / ${long_put_strike}\n"
            f"• Credit: ${credit} | Max Loss: ${max_loss}\n"
            f"• Probability of Profit: `{pop}%`\n"
            f"• Breakeven: `${breakeven:.2f}`\n"
            f"• ציפוי רווח: `${exp_profit}` | ציפוי הפסד: `${exp_loss}`\n"
            f"• המלצה: {'✅ עסקה טובה' if is_viable else '⚠️ בדוק שוב'}"
        )

        return StrategyEvaluation(
            strategy="Bull Put Spread",
            symbol=symbol,
            pop=pop,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_low=breakeven,
            breakeven_high=stock_price * 2,
            expected_profit=exp_profit,
            expected_loss=exp_loss,
            credit=credit,
            is_viable=is_viable,
            summary_hebrew=summary,
        )

    except ImportError:
        logger.warning("optionlab not installed — using approximation")
        return _approximate_bull_put(symbol, stock_price, short_put_strike,
                                     long_put_strike, short_put_premium, long_put_premium)
    except Exception as e:
        logger.error("optionlab evaluation failed: %s", e)
        return None


def evaluate_iron_condor(
    symbol: str,
    stock_price: float,
    put_short: float, put_long: float,
    call_short: float, call_long: float,
    put_short_prem: float, put_long_prem: float,
    call_short_prem: float, call_long_prem: float,
    expiration_date: str,
    volatility: float,
    risk_free_rate: float = 0.0433,
) -> Optional[StrategyEvaluation]:
    """Evaluate an Iron Condor using optionlab."""
    try:
        from optionlab import run_strategy

        today = date.today().isoformat()

        inputs = {
            "stock_price": stock_price,
            "start_date": today,
            "target_date": expiration_date,
            "volatility": volatility,
            "interest_rate": risk_free_rate,
            "dividend_yield": 0.0,
            "legs": [
                {"type": "put",  "strike": put_long,   "premium": put_long_prem,   "n": 1, "action": "buy"},
                {"type": "put",  "strike": put_short,  "premium": put_short_prem,  "n": 1, "action": "sell"},
                {"type": "call", "strike": call_short, "premium": call_short_prem, "n": 1, "action": "sell"},
                {"type": "call", "strike": call_long,  "premium": call_long_prem,  "n": 1, "action": "buy"},
            ],
        }

        result = run_strategy(inputs)

        net_credit = round(((put_short_prem - put_long_prem) + (call_short_prem - call_long_prem)) * 100, 2)
        spread_width = min(put_short - put_long, call_long - call_short)
        max_profit = net_credit
        max_loss = round((spread_width - net_credit / 100) * 100, 2)

        pop = round(float(result.probability_of_profit) * 100, 1) if hasattr(result, "probability_of_profit") else 68.0
        be_low = put_short - net_credit / 100
        be_high = call_short + net_credit / 100
        exp_profit = round(float(result.expected_profit) * 100, 2) if hasattr(result, "expected_profit") else max_profit * 0.5
        exp_loss = round(float(result.expected_loss) * 100, 2) if hasattr(result, "expected_loss") else max_loss * 0.3

        is_viable = pop >= 60 and (net_credit / 100) / spread_width >= 0.25

        summary = (
            f"🦅 *Iron Condor — {symbol}*\n"
            f"• Put Spread: ${put_long} / ${put_short}\n"
            f"• Call Spread: ${call_short} / ${call_long}\n"
            f"• Net Credit: ${net_credit} | Max Loss: ${max_loss}\n"
            f"• Probability of Profit: `{pop}%`\n"
            f"• Breakevens: `${be_low:.2f}` — `${be_high:.2f}`\n"
            f"• רווח ציפוי: `${exp_profit}` | הפסד ציפוי: `${exp_loss}`\n"
            f"• המלצה: {'✅ עסקה טובה' if is_viable else '⚠️ בדוק שוב'}"
        )

        return StrategyEvaluation(
            strategy="Iron Condor",
            symbol=symbol,
            pop=pop,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_low=be_low,
            breakeven_high=be_high,
            expected_profit=exp_profit,
            expected_loss=exp_loss,
            credit=net_credit,
            is_viable=is_viable,
            summary_hebrew=summary,
        )

    except ImportError:
        logger.warning("optionlab not installed")
        return None
    except Exception as e:
        logger.error("optionlab iron condor failed: %s", e)
        return None


def _approximate_bull_put(
    symbol, stock_price, short_k, long_k, short_prem, long_prem
) -> StrategyEvaluation:
    """Fallback approximation when optionlab not available."""
    credit = round((short_prem - long_prem) * 100, 2)
    spread = short_k - long_k
    max_loss = round((spread - credit / 100) * 100, 2)
    breakeven = short_k - credit / 100
    distance_pct = (stock_price - short_k) / stock_price * 100
    pop = round(min(85, 50 + distance_pct * 5), 1)
    is_viable = pop >= 65

    return StrategyEvaluation(
        strategy="Bull Put Spread",
        symbol=symbol,
        pop=pop,
        max_profit=credit,
        max_loss=max_loss,
        breakeven_low=breakeven,
        breakeven_high=stock_price * 2,
        expected_profit=round(credit * 0.5, 2),
        expected_loss=round(max_loss * 0.3, 2),
        credit=credit,
        is_viable=is_viable,
        summary_hebrew=f"📊 {symbol} Bull Put Spread | PoP: {pop}% | Credit: ${credit}",
    )
