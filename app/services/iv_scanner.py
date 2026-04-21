"""
iv_scanner.py — High IV Scanner with Reason Detection
======================================================

Scans for stocks with elevated IV and explains WHY.

IV Level Classification:
- IV < 25%:   LOW     — buy options (LEAPs, debit spreads)
- IV 25-50%:  MEDIUM  — selective credit spreads
- IV 50-70%:  HIGH    — good for selling premium
- IV 70-100%: VERY_HIGH — excellent premium selling
- IV > 100%:  EXTREME — meme/earnings/catalyst event

IV Rank Classification:
- IV Rank < 30%: LOW
- IV Rank 30-50%: MEDIUM
- IV Rank 50-70%: HIGH    — consider selling premium
- IV Rank > 70%: VERY_HIGH — strong sell signal

Sources: iv-tracker dashboard methodology, gregor-nelson/OptionsScanner scan logic,
         George-Dros/Volatility_Surface IV surface analysis
"""

import logging
import math
from dataclasses import dataclass
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SCAN_LIST = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL",
    "AMD", "COIN", "MSTR", "PLTR", "RBLX", "HOOD",
    "SPY", "QQQ", "IWM", "GLD", "TLT",
    "XOM", "JPM", "BAC", "GS", "NFLX", "CRM",
]


@dataclass
class IVScanResult:
    ticker: str
    price: float
    iv_current: float
    iv_rank: float
    iv_percentile: float
    iv_52w_low: float
    iv_52w_high: float
    iv_level: str           # "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH" | "EXTREME"
    iv_rank_level: str      # "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH"
    has_earnings_soon: bool
    earnings_date: Optional[str]
    earnings_days_away: Optional[int]
    news_catalyst: str
    short_interest: float
    recent_move_pct: float
    recommended_strategy: str
    strategy_reason: str
    expected_move: float
    opportunity_score: float


def _classify_iv(iv: float) -> str:
    if iv < 25:
        return "LOW"
    elif iv < 50:
        return "MEDIUM"
    elif iv < 70:
        return "HIGH"
    elif iv < 100:
        return "VERY_HIGH"
    return "EXTREME"


def _classify_iv_rank(rank: float) -> str:
    if rank < 30:
        return "LOW"
    elif rank < 50:
        return "MEDIUM"
    elif rank < 70:
        return "HIGH"
    return "VERY_HIGH"


def _get_strategy(
    iv: float, iv_rank: float, has_earnings: bool,
    trend: str, earnings_days: Optional[int],
) -> tuple[str, str]:
    if has_earnings and earnings_days is not None and earnings_days <= 7:
        return (
            "Pre-Earnings Strangle (קנה)",
            f"Earnings בעוד {earnings_days} ימים — קנה תנודתיות לפני, מכור אחרי IV Crush",
        )
    if iv > 100:
        return (
            "Short Strangle / Iron Condor (מכור)",
            "IV קיצוני — פרמיה עשירה ביותר. מכור Strangle רחב עם ניהול סיכון קפדני",
        )
    if iv_rank >= 70 and iv >= 50:
        if trend == "bullish":
            return (
                "Bull Put Spread (מכור פרמיה)",
                f"IV Rank {iv_rank:.0f}% + מגמה שורית — מכור Bull Put Spread, רווח מ-IV Crush + Theta",
            )
        elif trend == "bearish":
            return (
                "Bear Call Spread (מכור פרמיה)",
                f"IV Rank {iv_rank:.0f}% + מגמה דובית — מכור Bear Call Spread",
            )
        return (
            "Iron Condor (מכור פרמיה)",
            f"IV Rank {iv_rank:.0f}% + ניטרלי — Iron Condor אידאלי, קבל פרמיה משני הצדדים",
        )
    if iv_rank >= 50 and iv >= 35:
        return (
            "Cash-Secured Put / Covered Call",
            f"IV Rank {iv_rank:.0f}% — טוב להתחיל Wheel Strategy, פרמיה מעל הממוצע",
        )
    if iv_rank < 30:
        return (
            "Long Call LEAPs (קנה)",
            f"IV Rank {iv_rank:.0f}% — IV נמוך היסטורית → אופציות זולות → קנה LEAPs 6-12 חודש",
        )
    return (
        "המתן לIV גבוה יותר",
        f"IV Rank {iv_rank:.0f}% — בינוני, אין יתרון ברור. חכה ל-IV Rank > 50%",
    )


def _detect_iv_reason(
    ticker: str, iv: float, iv_rank: float,
    recent_move: float, short_pct: float,
    has_earnings: bool, earnings_days: Optional[int],
) -> str:
    reasons = []

    if has_earnings and earnings_days is not None:
        if earnings_days <= 3:
            reasons.append(f"🚨 Earnings בעוד {earnings_days} ימים — IV נפוח מאוד לפני הדוח")
        elif earnings_days <= 14:
            reasons.append(f"📅 Earnings בעוד {earnings_days} ימים — שוק מתמחר תנודה")
        else:
            reasons.append(f"📅 Earnings בעוד {earnings_days} ימים — השפעה מוגבלת")

    if abs(recent_move) >= 10:
        direction = "עלייה" if recent_move > 0 else "ירידה"
        reasons.append(f"📈 {direction} חדה של {abs(recent_move):.1f}% ב-5 ימים — שוק מצפה להמשך תנועה")
    elif abs(recent_move) >= 5:
        direction = "עלייה" if recent_move > 0 else "ירידה"
        reasons.append(f"📊 {direction} של {abs(recent_move):.1f}% לאחרונה — מומנטום גבוה")

    if short_pct >= 20:
        reasons.append(f"🎯 Short Interest {short_pct:.0f}% — סיכון Short Squeeze מעלה IV")
    elif short_pct >= 10:
        reasons.append(f"⚠️ Short Interest {short_pct:.0f}% — לחץ שורטים מתון")

    if iv >= 100:
        reasons.append("🔥 IV קיצוני (100%+) — אירוע ספציפי: earnings, FDA, M&A, או מניית meme")
    elif iv >= 70:
        reasons.append("🔥 IV גבוה מאוד — תנודתיות מוגברת, שוק מצפה לתנועה חדה")

    if iv_rank >= 80:
        reasons.append(f"📊 IV Rank {iv_rank:.0f}% — הכי גבוה שהיה ב-52 שבועות האחרונים")
    elif iv_rank >= 60:
        reasons.append(f"📊 IV Rank {iv_rank:.0f}% — גבוה ביחס להיסטוריה")

    if not reasons:
        if iv_rank >= 50:
            reasons.append(f"IV Rank {iv_rank:.0f}% — גבוה יחסית ללא זרז ספציפי ברור")
        else:
            reasons.append("IV בינוני — אין זרז ספציפי")

    return " | ".join(reasons)


def scan_high_iv(
    tickers: list[str] = None,
    min_iv_rank: float = 50.0,
    min_iv: float = 30.0,
    max_results: int = 10,
) -> list[IVScanResult]:
    """
    Finds stocks with high IV and explains why.
    Results sorted by opportunity_score descending.
    """
    import yfinance as yf
    import numpy as np

    if tickers is None:
        tickers = DEFAULT_SCAN_LIST

    results = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            if hist.empty or len(hist) < 50:
                continue

            closes = hist["Close"]
            price = float(closes.iloc[-1])

            returns = closes.pct_change().dropna()
            hv_30 = float(returns.rolling(30).std().iloc[-1]) * math.sqrt(252) * 100
            iv_current = hv_30

            try:
                expirations = stock.options
                if expirations:
                    today = date.today()
                    target_exp = None
                    for exp in expirations:
                        dte = (date.fromisoformat(exp) - today).days
                        if 20 <= dte <= 50:
                            target_exp = exp
                            break
                    if target_exp is None:
                        target_exp = expirations[0]

                    chain = stock.option_chain(target_exp)
                    atm_calls = chain.calls[abs(chain.calls["strike"] - price) < price * 0.03]
                    atm_puts = chain.puts[abs(chain.puts["strike"] - price) < price * 0.03]
                    iv_values = (
                        atm_calls["impliedVolatility"].dropna().tolist()
                        + atm_puts["impliedVolatility"].dropna().tolist()
                    )
                    if iv_values:
                        iv_current = float(np.median(iv_values)) * 100
            except Exception:
                pass

            if iv_current < min_iv:
                continue

            rolling_hv = returns.rolling(30).std().dropna() * math.sqrt(252) * 100
            iv_52w_low = float(rolling_hv.min())
            iv_52w_high = float(rolling_hv.max())
            iv_rank = (
                (iv_current - iv_52w_low) / (iv_52w_high - iv_52w_low) * 100
                if iv_52w_high > iv_52w_low else 50.0
            )
            iv_rank = max(0.0, min(100.0, iv_rank))

            if iv_rank < min_iv_rank:
                continue

            iv_pct_rank = float((rolling_hv < iv_current).mean() * 100)
            recent_5d = float((closes.iloc[-1] / closes.iloc[-6] - 1) * 100) if len(closes) > 6 else 0.0

            has_earnings = False
            earnings_date_str = None
            earnings_days_away = None
            try:
                cal = stock.calendar
                if cal is not None and not cal.empty and "Earnings Date" in cal.index:
                    earn = cal.loc["Earnings Date"]
                    if hasattr(earn, "iloc"):
                        earn = earn.iloc[0]
                    if hasattr(earn, "date"):
                        earn = earn.date()
                    days = (earn - date.today()).days
                    if -2 <= days <= 60:
                        has_earnings = True
                        earnings_date_str = earn.strftime("%d/%m/%Y")
                        earnings_days_away = days
            except Exception:
                pass

            short_pct = 0.0
            try:
                si = stock.info.get("shortPercentOfFloat", 0) or 0
                short_pct = si * 100
            except Exception:
                pass

            ma20 = float(closes.rolling(20).mean().iloc[-1])
            ma50 = float(closes.rolling(50).mean().iloc[-1])
            trend = "bullish" if ma20 > ma50 else ("bearish" if ma20 < ma50 else "neutral")

            em = price * (iv_current / 100) * math.sqrt(30 / 365)
            strategy, strategy_reason = _get_strategy(iv_current, iv_rank, has_earnings, trend, earnings_days_away)
            iv_reason = _detect_iv_reason(ticker, iv_current, iv_rank, recent_5d, short_pct, has_earnings, earnings_days_away)

            score = min(40.0, iv_rank * 0.4) + min(20.0, (iv_current - 30) * 0.4)
            if has_earnings and earnings_days_away is not None:
                if earnings_days_away <= 7:
                    score -= 20
                elif earnings_days_away <= 14:
                    score -= 10
            if short_pct > 20:
                score -= 10
            score = max(0.0, min(100.0, score))

            results.append(IVScanResult(
                ticker=ticker,
                price=round(price, 2),
                iv_current=round(iv_current, 1),
                iv_rank=round(iv_rank, 1),
                iv_percentile=round(iv_pct_rank, 1),
                iv_52w_low=round(iv_52w_low, 1),
                iv_52w_high=round(iv_52w_high, 1),
                iv_level=_classify_iv(iv_current),
                iv_rank_level=_classify_iv_rank(iv_rank),
                has_earnings_soon=has_earnings,
                earnings_date=earnings_date_str,
                earnings_days_away=earnings_days_away,
                news_catalyst=iv_reason,
                short_interest=round(short_pct, 1),
                recent_move_pct=round(recent_5d, 1),
                recommended_strategy=strategy,
                strategy_reason=strategy_reason,
                expected_move=round(em, 2),
                opportunity_score=round(score, 1),
            ))

            logger.info("IV scan %s: IV=%.1f%% Rank=%.1f%% Score=%.0f", ticker, iv_current, iv_rank, score)

        except Exception as e:
            logger.debug("IV scan failed for %s: %s", ticker, e)

    results.sort(key=lambda x: x.opportunity_score, reverse=True)
    return results[:max_results]


def fetch_x_mentions(tickers: list[str]) -> dict[str, str]:
    """
    Search X/Twitter mentions via Perplexity to explain IV catalyst.
    Perplexity Sonar includes real-time X posts in its results.
    Returns {ticker: one-line note}.
    """
    try:
        from app.services.perplexity_service import PerplexityService
        svc = PerplexityService()
        if not svc.is_available():
            return {}

        ticker_str = ", ".join(tickers[:5])
        query = (
            f"What is causing high implied volatility right now for these stocks: {ticker_str}? "
            f"Check for: earnings, FDA decisions, M&A rumors, product launches, short squeezes, "
            f"and recent mentions on X/Twitter. Answer in 1 short sentence per stock. "
            f"Today is {date.today()}."
        )
        answer = svc.ask(query)
        if not answer:
            return {}

        notes = {}
        for line in answer.split("\n"):
            for ticker in tickers:
                if ticker.upper() in line.upper() and len(line) > 10:
                    notes[ticker] = line.strip()[:100]
                    break
        return notes

    except Exception as e:
        logger.debug("X/Perplexity search failed: %s", e)
        return {}


def format_iv_scan_telegram(results: list[IVScanResult], perplexity_notes: dict = None) -> str:
    """Format IV scan results as Hebrew Telegram message."""
    if not results:
        return "⚠️ לא נמצאו מניות עם IV גבוה כרגע."

    level_emoji = {
        "LOW": "❄️", "MEDIUM": "🔵", "HIGH": "🔥",
        "VERY_HIGH": "🚨", "EXTREME": "💥",
    }
    rank_emoji = {
        "LOW": "📉", "MEDIUM": "➡️", "HIGH": "📈", "VERY_HIGH": "🚀",
    }

    lines = [
        f"🔥 *סורק IV גבוה — {date.today().strftime('%d/%m/%Y')}*",
        f"נמצאו {len(results)} מניות עם IV Rank > 50%\n",
    ]

    for i, r in enumerate(results[:8], 1):
        lv = level_emoji.get(r.iv_level, "🔵")
        rv = rank_emoji.get(r.iv_rank_level, "➡️")

        earn_str = ""
        if r.has_earnings_soon and r.earnings_days_away is not None:
            if r.earnings_days_away <= 3:
                earn_str = f"\n  🚨 *Earnings בעוד {r.earnings_days_away} ימים!*"
            else:
                earn_str = f"\n  📅 Earnings: {r.earnings_date} ({r.earnings_days_away}d)"

        x_note = ""
        if perplexity_notes and r.ticker in perplexity_notes:
            x_note = f"\n  🐦 X: {perplexity_notes[r.ticker][:80]}"

        lines.append(
            f"*{i}. {r.ticker}* | ${r.price}\n"
            f"  {lv} IV: `{r.iv_current:.0f}%` {rv} Rank: `{r.iv_rank:.0f}%`\n"
            f"  📐 Expected Move ±`${r.expected_move}`/30d\n"
            f"  🎯 אסטרטגיה: *{r.recommended_strategy}*\n"
            f"  💡 {r.strategy_reason}\n"
            f"  🔍 *למה IV גבוה:* {r.news_catalyst}"
            f"{earn_str}{x_note}"
        )

    lines.append(
        "\n━━━━━━━━━━━━━━━━\n"
        "📊 *מדריך IV:*\n"
        "❄️ <25% = נמוך | 🔵 25-50% = בינוני\n"
        "🔥 50-70% = גבוה | 🚨 70-100% = גבוה מאוד\n"
        "💥 100%+ = קיצוני (earnings/meme/catalyst)"
    )

    return "\n".join(lines)
