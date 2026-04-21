"""
options_chain_screener.py — Professional Options Chain Screener
===============================================================

Sources:
- gregor-nelson/OptionsScanner: chain scan + liquidity filters
- ycchew/etf_credit_spread: ETF credit spread scoring logic
- 2020dataanalysis/options-strategy-lab: BWB + risk-reward ranking
"""

import logging
import math
from dataclasses import dataclass
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OptionContractInfo:
    ticker: str
    expiration: str
    dte: int
    option_type: str
    strike: float
    bid: float
    ask: float
    mid: float
    iv: float
    delta: float
    open_interest: int
    volume: int
    spread_pct: float
    is_liquid: bool


@dataclass
class CreditSpreadOpportunity:
    ticker: str
    strategy: str
    expiration: str
    dte: int
    short_strike: float
    short_delta: float
    short_premium: float
    long_strike: float
    long_delta: float
    long_premium: float
    net_credit: float
    net_credit_pct: float
    max_loss: float
    max_profit: float
    breakeven: float
    spread_width: float
    risk_reward: float
    opportunity_score: float


def _calc_delta(S: float, K: float, T: float, iv: float, opt_type: str) -> float:
    try:
        from scipy.stats import norm
        if T <= 0 or iv <= 0:
            return (1.0 if S > K else 0.0) if opt_type == "call" else (-1.0 if S < K else 0.0)
        d1 = (math.log(S / K) + (0.045 + 0.5 * iv ** 2) * T) / (iv * math.sqrt(T))
        return float(norm.cdf(d1)) if opt_type == "call" else float(norm.cdf(d1) - 1)
    except Exception:
        dist = abs(S - K) / S
        base = 0.5 * math.exp(-dist * 8)
        return base if opt_type == "call" else -base


def screen_options_chain(
    ticker: str,
    min_oi: int = 100,
    max_spread_pct: float = 0.15,
    delta_min: float = 0.05,
    delta_max: float = 0.50,
    dte_min: int = 20,
    dte_max: int = 55,
) -> list[OptionContractInfo]:
    """
    Screen full options chain for liquid contracts within delta/DTE range.
    gregor-nelson/OptionsScanner methodology: OI + bid-ask + delta filters.
    """
    import yfinance as yf
    results = []
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if hist.empty:
            return []
        price = float(hist["Close"].iloc[-1])
        today = date.today()

        for exp in stock.options:
            dte = (date.fromisoformat(exp) - today).days
            if not (dte_min <= dte <= dte_max):
                continue
            T = dte / 365
            try:
                chain = stock.option_chain(exp)
                for opt_type, df in [("put", chain.puts), ("call", chain.calls)]:
                    if df.empty:
                        continue
                    for _, row in df.iterrows():
                        strike = float(row.get("strike", 0))
                        bid = float(row.get("bid", 0) or 0)
                        ask = float(row.get("ask", 0) or 0)
                        oi = int(row.get("openInterest", 0) or 0)
                        iv = float(row.get("impliedVolatility", 0) or 0)
                        if bid <= 0 or ask <= 0 or oi < min_oi:
                            continue
                        mid = (bid + ask) / 2
                        sp = (ask - bid) / mid if mid > 0 else 1.0
                        if sp > max_spread_pct:
                            continue
                        delta = _calc_delta(price, strike, T, iv, opt_type)
                        if not (delta_min <= abs(delta) <= delta_max):
                            continue
                        results.append(OptionContractInfo(
                            ticker=ticker, expiration=exp, dte=dte,
                            option_type=opt_type, strike=strike,
                            bid=bid, ask=ask, mid=round(mid, 3),
                            iv=round(iv * 100, 1), delta=round(delta, 3),
                            open_interest=oi,
                            volume=int(row.get("volume", 0) or 0),
                            spread_pct=round(sp * 100, 1),
                            is_liquid=sp < 0.10 and oi >= 200,
                        ))
            except Exception:
                continue
    except Exception as e:
        logger.error("Chain screen failed for %s: %s", ticker, e)
    return results


def find_best_credit_spread(
    ticker: str,
    direction: str = "neutral",
    min_credit_pct: float = 0.25,
) -> Optional[CreditSpreadOpportunity]:
    """
    Find best Bull Put Spread — ycchew/etf_credit_spread scoring logic.
    Short leg: 15-30 delta | Long leg: 5-15 delta | Same expiration.
    Score = credit% × 40 + R/R × 30 + liquidity × 30.
    """
    try:
        import yfinance as yf
        price = float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        contracts = screen_options_chain(ticker)
        if not contracts:
            return None

        puts = [c for c in contracts if c.option_type == "put"]
        best: Optional[CreditSpreadOpportunity] = None
        best_score = 0.0

        short_puts = [p for p in puts if -0.30 <= p.delta <= -0.15]
        long_puts = [p for p in puts if -0.15 <= p.delta <= -0.05]

        for sp in short_puts:
            for lp in long_puts:
                if lp.expiration != sp.expiration or lp.strike >= sp.strike:
                    continue
                width = sp.strike - lp.strike
                if width < 2:
                    continue
                credit = sp.bid - lp.ask
                if credit < 0.10:
                    continue
                cpct = credit / width
                if cpct < min_credit_pct:
                    continue
                max_profit = credit * 100
                max_loss = (width - credit) * 100
                rr = max_profit / max_loss if max_loss > 0 else 0.0
                liquidity_bonus = 15.0 if (sp.is_liquid and lp.is_liquid) else 0.0
                score = cpct * 40 + rr * 30 + liquidity_bonus
                if score > best_score:
                    best_score = score
                    best = CreditSpreadOpportunity(
                        ticker=ticker, strategy="Bull Put Spread",
                        expiration=sp.expiration, dte=sp.dte,
                        short_strike=sp.strike, short_delta=sp.delta,
                        short_premium=sp.bid, long_strike=lp.strike,
                        long_delta=lp.delta, long_premium=lp.ask,
                        net_credit=round(credit, 2),
                        net_credit_pct=round(cpct * 100, 1),
                        max_loss=round(max_loss, 2),
                        max_profit=round(max_profit, 2),
                        breakeven=round(sp.strike - credit, 2),
                        spread_width=width,
                        risk_reward=round(rr, 2),
                        opportunity_score=round(score, 1),
                    )
        return best
    except Exception as e:
        logger.error("Credit spread finder failed for %s: %s", ticker, e)
        return None


def find_broken_wing_butterfly(ticker: str) -> Optional[CreditSpreadOpportunity]:
    """
    Find Broken Wing Butterfly — 2020dataanalysis/options-strategy-lab methodology.
    Structure: Buy 1 far OTM put + Sell 2 ATM puts + Buy 1 closer OTM put = net credit.
    The asymmetry (wider lower wing) removes upside risk — only capped downside risk.
    """
    try:
        import yfinance as yf
        price = float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        contracts = screen_options_chain(ticker, delta_min=0.05, delta_max=0.50, min_oi=50)
        puts = sorted([c for c in contracts if c.option_type == "put"],
                      key=lambda x: x.strike, reverse=True)
        if len(puts) < 3:
            return None

        atm = min(puts, key=lambda p: abs(p.strike - price))
        uppers = [p for p in puts
                  if atm.strike < p.strike <= price * 1.03 and p.expiration == atm.expiration]
        lowers = [p for p in puts
                  if p.strike < atm.strike - 5 and p.expiration == atm.expiration]
        if not uppers or not lowers:
            return None

        upper = uppers[0]
        lower = lowers[0]
        net = 2 * atm.bid - upper.ask - lower.ask
        if net < 0.05:
            return None

        width = atm.strike - lower.strike
        max_loss = (width - net) * 100
        return CreditSpreadOpportunity(
            ticker=ticker, strategy="Broken Wing Butterfly 🦋",
            expiration=atm.expiration, dte=atm.dte,
            short_strike=atm.strike, short_delta=atm.delta,
            short_premium=atm.bid * 2, long_strike=lower.strike,
            long_delta=lower.delta, long_premium=lower.ask,
            net_credit=round(net, 2),
            net_credit_pct=round(net / width * 100, 1) if width > 0 else 0.0,
            max_loss=round(max_loss, 2),
            max_profit=round(net * 100, 2),
            breakeven=round(atm.strike - net, 2),
            spread_width=width,
            risk_reward=round(net * 100 / max(1.0, max_loss), 2),
            opportunity_score=round(net * 100, 1),
        )
    except Exception as e:
        logger.debug("BWB failed for %s: %s", ticker, e)
        return None


def format_credit_spread_hebrew(opp: CreditSpreadOpportunity) -> str:
    """Format CreditSpreadOpportunity as Hebrew Telegram message."""
    emoji = {
        "Bull Put Spread": "📈",
        "Bear Call Spread": "📉",
        "Iron Condor": "🦅",
        "Broken Wing Butterfly 🦋": "🦋",
    }.get(opp.strategy, "📊")
    return (
        f"{emoji} *{opp.strategy} — {opp.ticker}*\n"
        f"• פקיעה: `{opp.expiration}` ({opp.dte} DTE)\n"
        f"• Short: `${opp.short_strike}` | Long: `${opp.long_strike}`\n"
        f"• קרדיט: `${opp.net_credit}` ({opp.net_credit_pct:.0f}% מהרוחב)\n"
        f"• מקס רווח: `${opp.max_profit}` | מקס הפסד: `${opp.max_loss}`\n"
        f"• Breakeven: `${opp.breakeven}` | R/R: `{opp.risk_reward:.2f}`\n"
        f"• ציון: `{opp.opportunity_score:.0f}`"
    )
