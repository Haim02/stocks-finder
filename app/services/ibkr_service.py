"""
ibkr_service.py — Interactive Brokers Integration
===================================================

Sources:
- aicheung/0dte-trader: IBKR API order management logic
- vjsworld/IBKR-0DTE-SPX: Bloomberg-style SPX 0DTE signal
- IBKR Campus: ATM straddle expected-move formula

IBKR is disabled by default (IBKR_ENABLED=false).
All functions fail-safe — no IBKR connection = graceful None/fallback.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

IBKR_ENABLED = os.getenv("IBKR_ENABLED", "false").lower() == "true"
IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = int(os.getenv("IBKR_PORT", "7497"))
IBKR_TRADING_ENABLED = os.getenv("IBKR_TRADING_ENABLED", "false").lower() == "true"


def is_ibkr_available() -> bool:
    """Check if TWS/Gateway is running and accepting connections."""
    if not IBKR_ENABLED:
        return False
    try:
        import socket
        s = socket.socket()
        s.settimeout(2)
        result = s.connect_ex((IBKR_HOST, IBKR_PORT))
        s.close()
        return result == 0
    except Exception:
        return False


def get_real_iv_from_ibkr(ticker: str) -> Optional[float]:
    """
    Get real IV directly from IBKR market data (tick type 106).
    More accurate for illiquid/meme stocks where yfinance options chain fails.
    Returns None if IBKR not connected — caller falls back to yfinance.
    """
    if not is_ibkr_available():
        return None
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.contract import Contract
        import threading

        iv_result: dict = {"value": None}
        done = threading.Event()

        class IVClient(EWrapper, EClient):
            def __init__(self):
                EClient.__init__(self, self)

            def tickOptionComputation(self, reqId, tickType, tickAttrib,
                                      impliedVol, *args):
                if impliedVol and impliedVol > 0:
                    iv_result["value"] = round(impliedVol * 100, 1)
                    done.set()

            def error(self, reqId, code, msg, *args):
                if code not in (2104, 2106, 2158):  # benign info codes
                    done.set()

        client = IVClient()
        client.connect(IBKR_HOST, IBKR_PORT, clientId=99)
        contract = Contract()
        contract.symbol = ticker
        contract.secType = "OPT"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.right = "P"
        client.reqMktData(1, contract, "106", False, False, [])
        threading.Thread(target=client.run, daemon=True).start()
        done.wait(timeout=5)
        client.disconnect()
        return iv_result.get("value")
    except ImportError:
        logger.debug("ibapi not installed — IBKR IV unavailable")
        return None
    except Exception as e:
        logger.debug("IBKR IV failed for %s: %s", ticker, e)
        return None


def get_spx_0dte_signal() -> dict:
    """
    SPX 0DTE straddle signal — vjsworld/IBKR-0DTE-SPX methodology.

    Compares recent actual intraday moves vs the straddle-implied expected move.
    - actual/expected > 1.2 → market underpricing movement → BUY straddle
    - actual/expected < 0.8 → market overpricing movement → SELL Iron Condor
    """
    try:
        import yfinance as yf
        import numpy as np

        spy = yf.Ticker("SPY")
        hist = spy.history(period="10d")
        if len(hist) < 5:
            return {"signal": "neutral", "reason": "נתונים לא מספיקים"}

        closes = hist["Close"]
        opens = hist["Open"]
        actual_moves = [
            abs(float(closes.iloc[-i]) - float(opens.iloc[-i]))
            for i in range(1, 5)
        ]
        mean_actual = float(np.mean(actual_moves))
        price = float(closes.iloc[-1])

        # Get ATM straddle price from nearest expiration
        expected_move = price * 0.007  # fallback ~0.7%
        try:
            exps = spy.options
            if exps:
                chain = spy.option_chain(exps[0])
                atm_c = chain.calls[abs(chain.calls["strike"] - price) < 2]
                atm_p = chain.puts[abs(chain.puts["strike"] - price) < 2]
                if not atm_c.empty and not atm_p.empty:
                    straddle = (
                        float(atm_c["lastPrice"].iloc[0])
                        + float(atm_p["lastPrice"].iloc[0])
                    )
                    expected_move = straddle * 0.85
        except Exception:
            pass

        ratio = mean_actual / expected_move if expected_move > 0 else 1.0

        if ratio > 1.2:
            return {
                "signal": "buy_straddle",
                "reason": (
                    f"SPX זז {mean_actual:.2f}$ בממוצע לעומת {expected_move:.2f}$ צפוי "
                    f"({(ratio - 1) * 100:.0f}% יותר) → קנה Straddle"
                ),
                "mean_actual": round(mean_actual, 2),
                "expected": round(expected_move, 2),
                "ratio": round(ratio, 2),
                "price": round(price, 2),
            }
        elif ratio < 0.8:
            return {
                "signal": "sell_condor",
                "reason": (
                    f"SPX זז {mean_actual:.2f}$ לעומת {expected_move:.2f}$ צפוי "
                    f"({(1 - ratio) * 100:.0f}% פחות) → מכור Iron Condor"
                ),
                "mean_actual": round(mean_actual, 2),
                "expected": round(expected_move, 2),
                "ratio": round(ratio, 2),
                "price": round(price, 2),
            }
        return {
            "signal": "neutral",
            "reason": f"תנועה בפועל ≈ צפויה ({ratio:.2f}x) → ניטרלי",
            "ratio": round(ratio, 2),
            "price": round(price, 2),
        }
    except Exception as e:
        return {"signal": "neutral", "reason": str(e)}
