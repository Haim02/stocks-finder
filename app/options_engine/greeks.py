"""
greeks.py — Black-Scholes Greeks Calculator
"""
import math
from dataclasses import dataclass

try:
    from scipy.stats import norm as _norm
    def _cdf(x): return _norm.cdf(x)
    def _pdf(x): return _norm.pdf(x)
except ImportError:
    def _cdf(x):
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    def _pdf(x):
        return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)


@dataclass
class Greeks:
    delta: float
    theta: float   # per calendar day ($)
    vega: float    # per 1% IV change ($)


def calculate_greeks(
    S: float, K: float, T: float, sigma: float,
    option_type: str = "call", r: float = 0.0433,
) -> Greeks:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return Greeks(0.0, 0.0, 0.0)

    d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)

    delta = _cdf(d1) if option_type == "call" else _cdf(d1) - 1
    vega = S * _pdf(d1) * math.sqrt(T) / 100
    theta_raw = (-(S * _pdf(d1) * sigma) / (2 * math.sqrt(T))
                 + (-r*K*math.exp(-r*T)*_cdf(d2) if option_type=="call"
                    else r*K*math.exp(-r*T)*_cdf(-d2)))
    theta = theta_raw / 365

    return Greeks(round(delta,4), round(theta,4), round(vega,4))


def get_risk_free_rate() -> float:
    try:
        from app.services.fred_service import get_macro_snapshot
        return get_macro_snapshot().fed_funds_rate / 100
    except Exception:
        return 0.0433
