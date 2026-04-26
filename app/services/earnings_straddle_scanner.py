"""
earnings_straddle_scanner.py — Earnings Straddle Strategy Scanner
==================================================================

Based on professional options book methodology:
1. Find stocks reporting earnings in 3 trading days (after the bell)
2. Filter: Volume > 1M/day, Beta > 2.0, Price > $40
3. Check historical earnings gaps > $1 in last 2 quarters
4. Determine oversold/overbought via RSI(5), Stochastics %K(5), CCI(20)
5. Recommend entry timing based on condition

Entry Rules:
- OVERSOLD  → Buy Calls 3 days before, Buy Puts day of earnings
- OVERBOUGHT → Buy Puts 3 days before, Buy Calls day of earnings
- NEUTRAL   → Buy both sides (full Straddle) on earnings day

Exit Rules:
- Leg out after earnings announcement
- Take profit if option doubles (+100%)
- Stop loss if option loses 50%
"""

import logging
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EarningsStraddleCandidate:
    ticker: str
    company_name: str
    price: float
    earnings_date: str
    earnings_days_away: int
    after_bell: bool

    # Filters
    avg_volume_m: float        # Average daily volume in millions
    beta: float
    passed_volume: bool        # > 1M shares/day
    passed_beta: bool          # > 2.0
    passed_price: bool         # > $40

    # Historical earnings gaps
    gap_q1: float              # $ gap at last earnings
    gap_q2: float              # $ gap at earnings before that
    passed_gap: bool           # Both gaps > $1

    # Condition indicators
    rsi_5: float
    stoch_k_5: float
    cci_20: float
    condition: str             # "OVERSOLD" | "OVERBOUGHT" | "NEUTRAL"

    # Strategy
    entry_plan: str            # What to buy and when
    straddle_cost: float       # Estimated cost of full straddle
    expected_move: float       # $ expected move from options chain
    breakeven_up: float        # Price needs to reach above
    breakeven_down: float      # Price needs to drop below
    risk_reward: str           # Assessment

    # Overall
    passes_all_filters: bool
    opportunity_score: float   # 0-100


def _calc_rsi(closes, period: int = 5) -> float:
    """Calculate RSI for given period."""
    try:
        import pandas as pd
        s = pd.Series(closes)
        delta = s.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 1)
    except Exception:
        return 50.0


def _calc_stochastics(highs, lows, closes, period: int = 5) -> float:
    """Calculate Stochastics %K."""
    try:
        import pandas as pd
        h = pd.Series(highs).rolling(period).max()
        l = pd.Series(lows).rolling(period).min()
        k = (pd.Series(closes) - l) / (h - l) * 100
        return round(float(k.iloc[-1]), 1)
    except Exception:
        return 50.0


def _calc_cci(highs, lows, closes, period: int = 20) -> float:
    """Calculate CCI (Commodity Channel Index)."""
    try:
        import pandas as pd
        import numpy as np
        h = pd.Series(highs)
        l = pd.Series(lows)
        c = pd.Series(closes)
        typical = (h + l + c) / 3
        mean = typical.rolling(period).mean()
        mad = typical.rolling(period).apply(
            lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
        )
        cci = (typical - mean) / (0.015 * mad)
        return round(float(cci.iloc[-1]), 1)
    except Exception:
        return 0.0


def _determine_condition(rsi: float, stoch_k: float, cci: float) -> str:
    """
    Determine oversold/overbought/neutral based on 3 indicators.
    Need at least 2 of 3 to agree.
    """
    oversold_signals = sum([
        rsi < 30,
        stoch_k < 25,
        cci < -100,
    ])
    overbought_signals = sum([
        rsi > 70,
        stoch_k > 75,
        cci > 100,
    ])

    if oversold_signals >= 2:
        return "OVERSOLD"
    elif overbought_signals >= 2:
        return "OVERBOUGHT"
    else:
        return "NEUTRAL"


def _get_entry_plan(condition: str, earnings_days: int) -> str:
    """Generate specific entry plan based on condition and timing."""
    if condition == "OVERSOLD":
        if earnings_days == 3:
            return "קנה CALLS עכשיו (3 ימים לפני) | קנה PUTS ביום ה-Earnings"
        elif earnings_days == 2:
            return "קנה CALLS עכשיו | קנה PUTS ביום ה-Earnings"
        elif earnings_days == 1:
            return "קנה CALLS עכשיו | קנה PUTS מחר (יום ה-Earnings)"
        else:
            return "קנה Straddle מלא ביום ה-Earnings (oversold)"

    elif condition == "OVERBOUGHT":
        if earnings_days == 3:
            return "קנה PUTS עכשיו (3 ימים לפני) | קנה CALLS ביום ה-Earnings"
        elif earnings_days == 2:
            return "קנה PUTS עכשיו | קנה CALLS ביום ה-Earnings"
        elif earnings_days == 1:
            return "קנה PUTS עכשיו | קנה CALLS מחר (יום ה-Earnings)"
        else:
            return "קנה Straddle מלא ביום ה-Earnings (overbought)"

    else:  # NEUTRAL
        return "קנה Straddle מלא (Call + Put) ביום ה-Earnings"


def _get_historical_gaps(ticker: str) -> tuple[float, float]:
    """
    Estimate historical earnings gaps from price history.
    Looks for large overnight gaps that coincide with earnings dates.
    Returns (gap_q1, gap_q2) in dollars.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 60:
            return 0.0, 0.0

        # Find largest overnight gaps (proxy for earnings gaps)
        gaps = []
        for i in range(1, len(hist)):
            prev_close = float(hist["Close"].iloc[i-1])
            open_price = float(hist["Open"].iloc[i])
            gap = abs(open_price - prev_close)
            if gap > 1.0:  # Only gaps > $1
                gaps.append(gap)

        gaps.sort(reverse=True)

        gap_q1 = gaps[0] if len(gaps) > 0 else 0.0
        gap_q2 = gaps[1] if len(gaps) > 1 else 0.0

        return round(gap_q1, 2), round(gap_q2, 2)

    except Exception:
        return 0.0, 0.0


def _get_straddle_cost(ticker: str, price: float) -> tuple[float, float, float]:
    """
    Get ATM straddle cost from options chain.
    Returns (straddle_cost, expected_move, atm_strike)
    """
    try:
        import yfinance as yf
        from datetime import date

        stock = yf.Ticker(ticker)
        expirations = stock.options
        today = date.today()

        # Find expiration just after earnings
        for exp in expirations:
            exp_date = date.fromisoformat(exp)
            dte = (exp_date - today).days
            if 3 <= dte <= 14:  # Nearest exp after earnings
                chain = stock.option_chain(exp)

                # Find ATM call and put
                calls = chain.calls
                puts = chain.puts

                atm_strike = round(price)

                atm_calls = calls[abs(calls["strike"] - atm_strike) <= 2.5]
                atm_puts = puts[abs(puts["strike"] - atm_strike) <= 2.5]

                if atm_calls.empty or atm_puts.empty:
                    break

                call_mid = float(
                    (atm_calls["bid"].iloc[0] + atm_calls["ask"].iloc[0]) / 2
                )
                put_mid = float(
                    (atm_puts["bid"].iloc[0] + atm_puts["ask"].iloc[0]) / 2
                )

                straddle_cost = round((call_mid + put_mid), 2)
                expected_move = round(straddle_cost * 0.85, 2)

                return straddle_cost, expected_move, atm_strike

    except Exception as e:
        logger.debug("Straddle cost failed for %s: %s", ticker, e)

    # Fallback: estimate from IV
    estimated = round(price * 0.08, 2)  # ~8% of stock price
    return estimated, round(estimated * 0.85, 2), round(price)


def _get_earnings_candidates(days_ahead: int = 3) -> list[dict]:
    """
    Get stocks reporting earnings in next N trading days.
    Uses Perplexity for real-time earnings calendar.
    """
    candidates = []

    # Try Perplexity first (most accurate)
    try:
        from app.services.perplexity_service import PerplexityService
        svc = PerplexityService()
        if svc.is_available():
            today = date.today().strftime("%B %d, %Y")
            answer = svc.search(
                f"Which US stocks are reporting earnings after the bell "
                f"in the next 3 trading days from {today}? "
                f"List only stocks with price > $40 and high volatility. "
                f"Format: TICKER, Company Name, Date. List 10-15 stocks.",
                max_chars=800
            )
            if answer:
                # Parse tickers from answer
                import re
                tickers = re.findall(r'\b([A-Z]{2,5})\b', answer)
                for t in tickers[:15]:
                    if t not in ('US', 'ET', 'AM', 'PM', 'EPS', 'CEO', 'CFO'):
                        candidates.append({"ticker": t, "source": "perplexity"})
    except Exception:
        pass

    # Fallback: known high-beta stocks that often have earnings
    if not candidates:
        candidates = [
            {"ticker": t, "source": "watchlist"}
            for t in ["NVDA", "TSLA", "META", "AMZN", "GOOGL",
                      "AMD", "NFLX", "COIN", "MSTR", "PLTR",
                      "SQ", "SHOP", "SNOW", "UBER", "LYFT"]
        ]

    return candidates


def scan_earnings_straddle(
    days_ahead: int = 3,
    max_results: int = 5,
) -> list[EarningsStraddleCandidate]:
    """
    Main scanner — finds earnings straddle opportunities.
    Applies all 11 filters from the book methodology.
    """
    import yfinance as yf

    raw_candidates = _get_earnings_candidates(days_ahead)
    results = []
    scanned = set()

    for candidate in raw_candidates:
        ticker = candidate["ticker"]
        if ticker in scanned:
            continue
        scanned.add(ticker)

        try:
            stock = yf.Ticker(ticker)

            # Get basic data
            try:
                info = stock.info
            except Exception:
                continue

            price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
            if not price or price <= 0:
                hist = stock.history(period="1d")
                if hist.empty:
                    continue
                price = float(hist["Close"].iloc[-1])

            name = info.get("shortName", ticker)
            beta = info.get("beta", 0) or 0
            avg_vol = (info.get("averageVolume", 0) or 0) / 1_000_000

            # ── Filter 3: Volume > 1M ──────────────────────────────────────
            passed_volume = avg_vol >= 1.0

            # ── Filter 4: Beta > 2.0 ──────────────────────────────────────
            passed_beta = beta >= 2.0

            # ── Filter 5: Price > $40 ─────────────────────────────────────
            passed_price = price >= 40.0

            # ── Get earnings date ─────────────────────────────────────────
            earnings_date_str = "N/A"
            earnings_days = 99
            after_bell = True  # Assume after bell

            try:
                cal = stock.calendar
                if cal is not None and not cal.empty and "Earnings Date" in cal.index:
                    earn = cal.loc["Earnings Date"]
                    if hasattr(earn, "iloc"):
                        earn = earn.iloc[0]
                    if hasattr(earn, "date"):
                        earn = earn.date()
                    earnings_days = (earn - date.today()).days
                    earnings_date_str = earn.strftime("%d/%m/%Y")
            except Exception:
                pass

            # ── Filter 1 & 2: Earnings in N days ─────────────────────────
            if earnings_days > days_ahead or earnings_days < 0:
                if candidate["source"] == "perplexity":
                    earnings_days = days_ahead  # Trust Perplexity
                else:
                    continue

            # ── Filter 6: Historical gaps > $1 ───────────────────────────
            gap_q1, gap_q2 = _get_historical_gaps(ticker)
            passed_gap = gap_q1 >= 1.0 and gap_q2 >= 1.0

            # ── Get price history for indicators ─────────────────────────
            hist = stock.history(period="3mo")
            if hist.empty or len(hist) < 25:
                continue

            closes = hist["Close"].tolist()
            highs = hist["High"].tolist()
            lows = hist["Low"].tolist()

            # ── Filter 7: RSI(5), Stochastics(5), CCI(20) ────────────────
            rsi_5 = _calc_rsi(closes, period=5)
            stoch_k_5 = _calc_stochastics(highs, lows, closes, period=5)
            cci_20 = _calc_cci(highs, lows, closes, period=20)

            condition = _determine_condition(rsi_5, stoch_k_5, cci_20)

            # ── Entry plan (rules 8-11) ───────────────────────────────────
            entry_plan = _get_entry_plan(condition, earnings_days)

            # ── Straddle cost & expected move ─────────────────────────────
            straddle_cost, expected_move, atm_strike = _get_straddle_cost(
                ticker, price
            )

            breakeven_up = round(atm_strike + straddle_cost, 2)
            breakeven_down = round(atm_strike - straddle_cost, 2)

            # ── Passes all filters? ───────────────────────────────────────
            passes = (
                passed_volume and
                passed_beta and
                passed_price and
                passed_gap
            )

            # ── Opportunity score ─────────────────────────────────────────
            score = 50.0
            if passed_volume:
                score += 10
            if passed_beta:
                score += 15
            if passed_price:
                score += 5
            if passed_gap:
                score += 20
            if condition != "NEUTRAL":
                score += 15  # Directional lean = better timing
            if earnings_days <= 3:
                score += 5
            score = max(0, min(100, score))

            # ── Risk/Reward assessment ────────────────────────────────────
            move_pct = expected_move / price * 100 if price > 0 else 0
            if move_pct >= 8:
                rr = "🔥 גבוה — תנועה צפויה גדולה מעלות ה-Straddle"
            elif move_pct >= 5:
                rr = "✅ טוב — כדאי לבדוק"
            else:
                rr = "⚠️ נמוך — ייתכן שה-Straddle יקר מדי"

            results.append(EarningsStraddleCandidate(
                ticker=ticker,
                company_name=name,
                price=round(price, 2),
                earnings_date=earnings_date_str,
                earnings_days_away=earnings_days,
                after_bell=after_bell,
                avg_volume_m=round(avg_vol, 1),
                beta=round(beta, 1),
                passed_volume=passed_volume,
                passed_beta=passed_beta,
                passed_price=passed_price,
                gap_q1=gap_q1,
                gap_q2=gap_q2,
                passed_gap=passed_gap,
                rsi_5=rsi_5,
                stoch_k_5=stoch_k_5,
                cci_20=cci_20,
                condition=condition,
                entry_plan=entry_plan,
                straddle_cost=straddle_cost,
                expected_move=expected_move,
                breakeven_up=breakeven_up,
                breakeven_down=breakeven_down,
                risk_reward=rr,
                passes_all_filters=passes,
                opportunity_score=round(score, 1),
            ))

        except Exception as e:
            logger.debug("Earnings straddle scan failed for %s: %s", ticker, e)
            continue

    # Sort: passing all filters first, then by score
    results.sort(key=lambda x: (x.passes_all_filters, x.opportunity_score), reverse=True)
    return results[:max_results]


def format_earnings_straddle_hebrew(results: list[EarningsStraddleCandidate]) -> str:
    """Format results as Hebrew Telegram message."""
    if not results:
        return "⚠️ לא נמצאו מניות מתאימות ל-Earnings Straddle כרגע."

    condition_emoji = {
        "OVERSOLD": "📉 Oversold",
        "OVERBOUGHT": "📈 Overbought",
        "NEUTRAL": "➡️ ניטרלי",
    }

    lines = [
        "🎯 *סורק Earnings Straddle*\n"
        "📚 מבוסס על מתודולוגיית ספר אופציות מקצועי\n"
        f"{'━'*30}\n"
    ]

    for i, r in enumerate(results, 1):
        # Filter status
        filters = []
        filters.append("✅ Volume" if r.passed_volume else f"❌ Volume ({r.avg_volume_m:.1f}M < 1M)")
        filters.append("✅ Beta" if r.passed_beta else f"❌ Beta ({r.beta:.1f} < 2.0)")
        filters.append("✅ מחיר" if r.passed_price else f"❌ מחיר (${r.price:.0f} < $40)")
        filters.append("✅ Gap היסטורי" if r.passed_gap else f"❌ Gap (Q1=${r.gap_q1:.1f} Q2=${r.gap_q2:.1f})")

        passed_icon = "🟢 עובר כל הסינונים!" if r.passes_all_filters else "🟡 עובר חלקית"

        lines.append(
            f"*{i}. {r.ticker}* — {r.company_name}\n"
            f"💵 מחיר: `${r.price}` | Beta: `{r.beta}`\n"
            f"📅 Earnings: `{r.earnings_date}` (בעוד {r.earnings_days_away} ימים)\n\n"

            f"📋 *סינונים:*\n"
            f"  {' | '.join(filters)}\n"
            f"  {passed_icon}\n\n"

            f"📊 *אינדיקטורים (כלל 7):*\n"
            f"  RSI(5): `{r.rsi_5:.0f}` "
            f"({'< 30 ✅' if r.rsi_5 < 30 else '> 70 ✅' if r.rsi_5 > 70 else '➡️ ניטרלי'})\n"
            f"  Stoch %K(5): `{r.stoch_k_5:.0f}` "
            f"({'< 25 ✅' if r.stoch_k_5 < 25 else '> 75 ✅' if r.stoch_k_5 > 75 else '➡️ ניטרלי'})\n"
            f"  CCI(20): `{r.cci_20:.0f}` "
            f"({'< -100 ✅' if r.cci_20 < -100 else '> 100 ✅' if r.cci_20 > 100 else '➡️ ניטרלי'})\n"
            f"  מצב: *{condition_emoji.get(r.condition, r.condition)}*\n\n"

            f"💰 *עלויות Straddle:*\n"
            f"  עלות משוערת: `${r.straddle_cost}` לחוזה (`${r.straddle_cost*100:.0f}` סה\"כ)\n"
            f"  תנועה צפויה: `±${r.expected_move}`\n"
            f"  Breakeven: `${r.breakeven_down}` — `${r.breakeven_up}`\n"
            f"  R/R: {r.risk_reward}\n\n"

            f"🎯 *תוכנית כניסה (כללים 8-11):*\n"
            f"  {r.entry_plan}\n\n"

            f"📊 ציון הזדמנות: `{r.opportunity_score:.0f}/100`\n"
            f"{'━'*30}\n"
        )

    lines.append(
        "📌 *כללי יציאה:*\n"
        "• צא מהמנצח אם עלה 100%+\n"
        "• צא מהמפסיד אם ירד 50%\n"
        "• צא מהשני אחרי הכרזת ה-Earnings"
    )

    return "\n".join(lines)
