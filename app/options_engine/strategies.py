"""
strategies.py — Strategy Selection + Strike Builder
"""
import math, logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategySetup:
    symbol: str
    price: float
    iv: float
    iv_rank: float
    strategy: str
    expiration: str
    dte: int
    strikes: dict = field(default_factory=dict)
    greeks: dict = field(default_factory=dict)
    credit: float = 0.0
    max_loss: float = 0.0
    probability_profit: float = 0.0
    return_on_risk: float = 0.0


def select_strategies(iv_rank: float) -> list[str]:
    if iv_rank > 0.6:
        return ["Iron Condor", "Bull Put Spread", "Bear Call Spread"]
    elif iv_rank < 0.3:
        return ["Bull Call Spread", "Bear Put Spread"]
    return ["Bull Put Spread", "Bear Call Spread"]


def _find_expiration(symbol: str, target_dte: int = 38) -> Optional[tuple[str, int]]:
    try:
        import yfinance as yf
        exps = yf.Ticker(symbol).options
        if not exps:
            return None
        today = date.today()
        best, best_diff = None, 999
        for exp in exps:
            try:
                exp_date = date.fromisoformat(exp)
                diff = abs((exp_date - today).days - target_dte)
                if diff < best_diff:
                    best_diff = diff
                    best = (exp, (exp_date - today).days)
            except ValueError:
                continue
        return best
    except Exception:
        return None


def _get_strike_near_delta(
    symbol: str, expiration: str, price: float, iv: float,
    target_delta: float = 0.20, option_type: str = "put"
) -> Optional[float]:
    try:
        import yfinance as yf
        from app.options_engine.greeks import calculate_greeks, get_risk_free_rate
        chain = yf.Ticker(symbol).option_chain(expiration)
        df = chain.puts if option_type == "put" else chain.calls
        if df.empty:
            return None

        T = max((_find_expiration(symbol) or ("", 38))[1] / 365, 0.001)
        r = get_risk_free_rate()

        df = df[df["strike"] < price].copy() if option_type == "put" \
            else df[df["strike"] > price].copy()
        if df.empty:
            return None

        best_strike, best_diff = None, 999
        for _, row in df.iterrows():
            K = float(row["strike"])
            sigma = float(row.get("impliedVolatility", iv) or iv)
            if sigma <= 0:
                sigma = iv
            g = calculate_greeks(price, K, T, sigma, option_type, r)
            diff = abs(abs(g.delta) - target_delta)
            if diff < best_diff:
                best_diff = diff
                best_strike = K
        return best_strike
    except Exception:
        # Fallback: expected move approximation
        T = 38/365
        em = price * iv * math.sqrt(T)
        if option_type == "put":
            return round(price - em * (target_delta / 0.16), 0)
        return round(price + em * (target_delta / 0.16), 0)


def build_setup(symbol: str, price: float, iv: float, iv_rank: float,
                strategy: str) -> Optional[StrategySetup]:
    from app.options_engine.greeks import calculate_greeks, get_risk_free_rate

    exp_result = _find_expiration(symbol)
    if not exp_result:
        return None
    expiration, dte = exp_result
    T = dte / 365
    r = get_risk_free_rate()
    strikes, greeks_data = {}, {}

    try:
        if strategy == "Bull Put Spread":
            put_sell = _get_strike_near_delta(symbol, expiration, price, iv, 0.20, "put")
            if not put_sell: return None
            put_buy = put_sell - 5
            strikes = {"put_sell": put_sell, "put_buy": put_buy}
            g = calculate_greeks(price, put_sell, T, iv, "put", r)
            greeks_data = {"delta": g.delta, "theta": g.theta, "vega": g.vega}
            credit = round(price * iv * math.sqrt(T) * 0.08, 2)
            max_loss = round((5 - credit) * 100, 2)

        elif strategy == "Bear Call Spread":
            call_sell = _get_strike_near_delta(symbol, expiration, price, iv, 0.20, "call")
            if not call_sell: return None
            call_buy = call_sell + 5
            strikes = {"call_sell": call_sell, "call_buy": call_buy}
            g = calculate_greeks(price, call_sell, T, iv, "call", r)
            greeks_data = {"delta": g.delta, "theta": g.theta, "vega": g.vega}
            credit = round(price * iv * math.sqrt(T) * 0.08, 2)
            max_loss = round((5 - credit) * 100, 2)

        elif strategy == "Iron Condor":
            put_sell = _get_strike_near_delta(symbol, expiration, price, iv, 0.17, "put")
            call_sell = _get_strike_near_delta(symbol, expiration, price, iv, 0.17, "call")
            if not put_sell or not call_sell: return None
            strikes = {"put_buy": put_sell-5, "put_sell": put_sell,
                      "call_sell": call_sell, "call_buy": call_sell+5}
            gp = calculate_greeks(price, put_sell, T, iv, "put", r)
            gc = calculate_greeks(price, call_sell, T, iv, "call", r)
            greeks_data = {
                "delta": round(gp.delta + gc.delta, 4),
                "theta": round(gp.theta + gc.theta, 4),
                "vega": round(gp.vega + gc.vega, 4),
            }
            credit = round(price * iv * math.sqrt(T) * 0.14, 2)
            max_loss = round((5 - credit) * 100, 2)

        elif strategy in ("Bull Call Spread", "Bear Put Spread"):
            opt = "call" if strategy == "Bull Call Spread" else "put"
            long_k = _get_strike_near_delta(symbol, expiration, price, iv, 0.50, opt)
            if not long_k: return None
            short_k = long_k + 10 if opt == "call" else long_k - 10
            strikes = ({"call_buy": long_k, "call_sell": short_k} if opt == "call"
                      else {"put_buy": long_k, "put_sell": short_k})
            g = calculate_greeks(price, long_k, T, iv, opt, r)
            greeks_data = {"delta": g.delta, "theta": g.theta, "vega": g.vega}
            credit = 0.0
            max_loss = round(price * iv * math.sqrt(T) * 0.05 * 100, 2)
        else:
            return None

        prob_profit = round((1 - abs(greeks_data.get("delta", 0.2))) * 100, 1)
        ror = round(credit / (max_loss/100) * 100, 1) if max_loss > 0 and credit > 0 else 0.0

        return StrategySetup(
            symbol=symbol, price=price, iv=round(iv*100,1), iv_rank=iv_rank,
            strategy=strategy, expiration=expiration, dte=dte, strikes=strikes,
            greeks=greeks_data, credit=credit, max_loss=max_loss,
            probability_profit=prob_profit, return_on_risk=ror,
        )
    except Exception as e:
        logger.error("build_setup failed %s %s: %s", symbol, strategy, e)
        return None
