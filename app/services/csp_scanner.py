"""
csp_scanner.py — Cash Secured Put Scanner
==========================================
Scans for CSP opportunities by price range and liquidity.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)

# Universe of optionable stocks — organized by price range
CSP_UNIVERSE = {
    "under_10": ["SOFI", "PLTR", "HOOD", "BBAI", "IONQ", "OPEN",
                 "CLOV", "WKHS", "GOEV", "NKLA", "RKT", "UWMC"],
    "10_to_20": ["F", "RIVN", "NIO", "XPEV", "GRAB", "JOBY",
                 "LCID", "WISH", "MVIS", "SNDL", "IREN", "CIFR"],
    "20_to_50": ["BAC", "WBA", "T", "INTC", "KEY", "RF",
                 "SNAP", "UBER", "LYFT", "SQ", "PYPL", "COIN"],
    "any": [],  # filled dynamically from Finviz
}


@dataclass
class CSPOpportunity:
    ticker: str
    company_name: str
    price: float
    # Best CSP setup
    expiration: str
    dte: int
    strike: float           # OTM put strike (below current price)
    strike_pct_otm: float   # % below current price
    bid: float
    premium_pct: float      # Premium as % of strike (annualized)
    iv_rank: float
    delta: float
    open_interest: int
    is_liquid: bool
    # Risk metrics
    breakeven: float        # Strike - premium received
    max_profit: float       # Premium * 100 per contract
    cash_required: float    # Strike * 100 (cash to secure)
    annual_return: float    # Annualized return %
    # Stock quality
    trend: str
    rsi: float
    has_earnings_soon: bool
    earnings_days: Optional[int]
    reason: str             # Why this CSP is good


def _find_best_csp_strike(ticker: str, price: float,
                           target_delta: float = 0.25) -> Optional[dict]:
    """Find the best CSP strike from options chain."""
    import yfinance as yf
    import numpy as np
    from datetime import date

    try:
        stock = yf.Ticker(ticker)
        today = date.today()

        for exp in stock.options[:6]:
            exp_date = date.fromisoformat(exp)
            dte = (exp_date - today).days
            if not (21 <= dte <= 50):
                continue

            chain = stock.option_chain(exp)
            puts = chain.puts

            if puts.empty:
                continue

            # Filter: OTM puts only (strike < price)
            puts = puts[
                (puts["strike"] < price * 0.98) &   # at least 2% OTM
                (puts["strike"] > price * 0.70) &   # not too far OTM
                (puts["bid"] > 0.05) &              # has real bid
                (puts["openInterest"] > 50)          # liquid enough
            ]

            if puts.empty:
                continue

            # Find strike closest to target delta (~0.25)
            # Approximate: closer to ATM = higher delta
            puts = puts.copy()
            puts["pct_otm"] = (price - puts["strike"]) / price * 100
            puts["delta_approx"] = 0.5 * np.exp(-puts["pct_otm"] / 10)

            # Find closest to 0.20-0.30 delta
            target = puts[
                (puts["delta_approx"] >= 0.15) &
                (puts["delta_approx"] <= 0.35)
            ]

            if target.empty:
                target = puts

            best = target.loc[target["bid"].idxmax()]

            strike = float(best["strike"])
            bid = float(best["bid"])
            oi = int(best["openInterest"] or 0)
            iv = float(best.get("impliedVolatility", 0.3) or 0.3) * 100

            premium_pct = bid / strike * 100
            annual_return = premium_pct * (365 / dte)
            breakeven = strike - bid

            spread = float(best["ask"]) - bid if "ask" in best else bid * 0.2
            is_liquid = (spread / bid < 0.15) and oi >= 100

            return {
                "expiration": exp,
                "dte": dte,
                "strike": strike,
                "strike_pct_otm": round((price - strike) / price * 100, 1),
                "bid": round(bid, 2),
                "premium_pct": round(premium_pct, 2),
                "iv_rank": round(iv, 1),
                "delta": round(float(best.get("delta_approx", 0.2)), 2),
                "open_interest": oi,
                "is_liquid": is_liquid,
                "breakeven": round(breakeven, 2),
                "max_profit": round(bid * 100, 2),
                "cash_required": round(strike * 100, 2),
                "annual_return": round(annual_return, 1),
            }
    except Exception as e:
        logger.debug("CSP strike search failed for %s: %s", ticker, e)
    return None


def scan_csp_opportunities(
    max_price: float = 20.0,
    min_price: float = 3.0,
    min_annual_return: float = 15.0,
    min_iv_rank: float = 20.0,
    max_results: int = 8,
    custom_tickers: list = None,
) -> list[CSPOpportunity]:
    """
    Main CSP scanner — finds best CSP setups under max_price.
    """
    import yfinance as yf

    # Build scan universe
    universe = custom_tickers or []
    if not universe:
        if max_price <= 10:
            universe = CSP_UNIVERSE["under_10"]
        elif max_price <= 20:
            universe = CSP_UNIVERSE["under_10"] + CSP_UNIVERSE["10_to_20"]
        else:
            universe = (CSP_UNIVERSE["under_10"] +
                       CSP_UNIVERSE["10_to_20"] +
                       CSP_UNIVERSE["20_to_50"])

        # Also get from Finviz
        try:
            from app.services.finviz_service import FinvizService
            finviz = FinvizService.get_bullish_tickers(n=20)
            universe = list(set(universe + finviz))
        except Exception:
            pass

    results = []

    for ticker in universe:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")
            if hist.empty:
                continue

            price = float(hist["Close"].iloc[-1])

            # Price filter
            if not (min_price <= price <= max_price):
                continue

            # Get company name
            try:
                name = stock.info.get("shortName", ticker)
            except Exception:
                name = ticker

            # Momentum check
            closes = hist["Close"]
            ma20 = float(closes.rolling(20).mean().iloc[-1])
            rsi_delta = closes.diff()
            gain = rsi_delta.where(rsi_delta > 0, 0).rolling(14).mean()
            loss = (-rsi_delta.where(rsi_delta < 0, 0)).rolling(14).mean()
            rsi = float(100 - (100 / (1 + gain/loss)).iloc[-1])

            trend = "bullish" if price > ma20 else "bearish"

            # Skip heavily bearish stocks
            if trend == "bearish" and rsi < 35:
                continue

            # Earnings check
            has_earnings = False
            earnings_days = None
            try:
                cal = stock.calendar
                if cal is not None and not cal.empty and "Earnings Date" in cal.index:
                    earn = cal.loc["Earnings Date"]
                    if hasattr(earn, "iloc"):
                        earn = earn.iloc[0]
                    if hasattr(earn, "date"):
                        earn = earn.date()
                    days = (earn - date.today()).days
                    if 0 <= days <= 14:
                        has_earnings = True
                        earnings_days = days
            except Exception:
                pass

            # Skip if earnings very soon
            if has_earnings and earnings_days and earnings_days <= 5:
                continue

            # Find best CSP strike
            csp = _find_best_csp_strike(ticker, price)
            if not csp:
                continue

            # Filter by return threshold
            if csp["annual_return"] < min_annual_return:
                continue

            # Build reason
            reason_parts = []
            if csp["annual_return"] >= 30:
                reason_parts.append(f"תשואה שנתית גבוהה {csp['annual_return']:.0f}%")
            if trend == "bullish":
                reason_parts.append("מגמה שורית")
            if csp["is_liquid"]:
                reason_parts.append("נזילה טובה")
            if not has_earnings:
                reason_parts.append("ללא Earnings קרובים")
            if rsi < 50:
                reason_parts.append(f"RSI {rsi:.0f} — לא overbought")

            results.append(CSPOpportunity(
                ticker=ticker,
                company_name=name,
                price=round(price, 2),
                expiration=csp["expiration"],
                dte=csp["dte"],
                strike=csp["strike"],
                strike_pct_otm=csp["strike_pct_otm"],
                bid=csp["bid"],
                premium_pct=csp["premium_pct"],
                iv_rank=csp["iv_rank"],
                delta=csp["delta"],
                open_interest=csp["open_interest"],
                is_liquid=csp["is_liquid"],
                breakeven=csp["breakeven"],
                max_profit=csp["max_profit"],
                cash_required=csp["cash_required"],
                annual_return=csp["annual_return"],
                trend=trend,
                rsi=round(rsi, 1),
                has_earnings_soon=has_earnings,
                earnings_days=earnings_days,
                reason=" | ".join(reason_parts),
            ))

        except Exception as e:
            logger.debug("CSP scan failed for %s: %s", ticker, e)
            continue

    # Sort by annual return
    results.sort(key=lambda x: x.annual_return, reverse=True)
    return results[:max_results]


def format_csp_hebrew(results: list[CSPOpportunity]) -> str:
    if not results:
        return "⚠️ לא נמצאו הזדמנויות CSP עם הקריטריונים האלה כרגע."

    lines = [
        f"💰 *סורק Cash Secured Put*\n"
        f"📅 {date.today().strftime('%d/%m/%Y')}\n"
        f"נמצאו {len(results)} הזדמנויות\n"
        f"{'━'*30}\n"
    ]

    for i, r in enumerate(results, 1):
        trend_e = "📈" if r.trend == "bullish" else "📉"
        liq_e = "✅" if r.is_liquid else "⚠️"
        earn_str = f"\n  ⚠️ Earnings בעוד {r.earnings_days}d — זהירות" if r.has_earnings_soon else ""

        lines.append(
            f"*{i}. {r.ticker}* — {r.company_name}\n"
            f"  💹 מחיר: `${r.price}` {trend_e} | RSI: `{r.rsi:.0f}`\n"
            f"  🎯 Strike: `${r.strike}` ({r.strike_pct_otm:.1f}% מחוץ לכסף)\n"
            f"  💰 פרמיה: `${r.bid}` ({r.premium_pct:.1f}% מה-Strike)\n"
            f"  📅 פקיעה: `{r.expiration}` ({r.dte} ימים)\n"
            f"  📊 תשואה שנתית: `{r.annual_return:.0f}%`\n"
            f"  💵 מזומן נדרש: `${r.cash_required:,.0f}` לחוזה\n"
            f"  📈 רווח מקסימלי: `${r.max_profit}` | Breakeven: `${r.breakeven}`\n"
            f"  {liq_e} נזילות: OI=`{r.open_interest}`"
            f"{earn_str}\n"
            f"  💡 {r.reason}\n"
        )

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *זכור:* CSP = אתה מוכן לקנות 100 מניות במחיר ה-Strike\n"
        "סגור ב-50% רווח | צא אם המניה מתחת ל-Breakeven"
    )

    return "\n".join(lines)
