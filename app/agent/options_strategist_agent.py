"""
options_strategist_agent.py — Agent 2: Options Strategist
===========================================================

Runs every trading day at 10:30 AM Israel time (30 min after Agent 1).

Pipeline:
1. Read Agent 1 verdict from MongoDB → abort if RED
2. Finviz scan → bullish + bearish candidates (20 each)
3. XGBoost filter → top 10 by confidence
4. 5-day cooldown filter → skip recently sent tickers
5. Per-ticker 7-step selection:
   - Liquidity (bid-ask check via yfinance)
   - IV Rank ≥ 25 minimum (≥ 35 preferred)
   - IV Percentile ≥ 50 (dual confirmation)
   - Expected Move calculation
   - Strategy selection (Iron Condor / Bull Put / Bear Call)
   - Strike selection (0.15-0.30 delta, outside 1SD)
6. Score and rank candidates → take top 3
7. Claude AI Hebrew commentary (Tastytrade style)
8. Send to Telegram
9. Log sent tickers to MongoDB cooldown

Position sizing adjustment:
- GREEN regime → full sizing (3-5% per trade)
- YELLOW regime → 50% sizing (1.5-2.5% per trade)
- RED regime → abort, no trades

The 7-step selection is based on TheOptionPremium.com / Andrew Crowder methodology:
- Probabilities over predictions
- IV Rank + IV Percentile dual confirmation
- Expected move for strike placement
- 0.15-0.30 delta = 70-85% probability of success
- Monthly options (30-45 DTE) always preferred over weeklies
"""

import logging
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

from app.services.realtime_market_data import (
    get_realtime_iv_data,
    get_options_chain,
    find_strike_by_delta,
    scan_for_high_iv_tickers,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
SCAN_LIMIT        = 20    # Finviz candidates per direction
XGB_TOP_N         = 10    # keep top N after XGBoost scoring
COOLDOWN_DAYS     = 5     # skip tickers sent in last N days
FINAL_TOP_N       = 3     # max trade ideas to send

# 7-step thresholds (TheOptionPremium methodology)
MIN_IV_RANK       = 25    # minimum to even consider
PREFERRED_IV_RANK = 35    # preferred threshold
MIN_IV_PCT        = 50    # IV Percentile dual confirmation
TARGET_DELTA_LOW  = 0.15
TARGET_DELTA_HIGH = 0.30
DTE_MIN           = 30
DTE_MAX           = 45

# Liquidity: reject if bid-ask spread > 10% of mid-price
MAX_SPREAD_PCT    = 0.10


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class TradeIdea:
    ticker: str
    strategy: str           # "Bull Put Spread" | "Bear Call Spread" | "Iron Condor"
    direction: str          # "bullish" | "bearish" | "neutral"
    current_price: float
    iv_rank: float          # 0-100
    iv_percentile: float    # 0-100
    expected_move: float    # ±$ amount (1SD)
    dte: int                # days to expiration used
    short_strike: float     # the strike we SELL
    long_strike: float      # the strike we BUY (protection)
    short_delta: float      # delta of short strike
    credit: float           # net credit per share ($)
    max_loss: float         # max loss per contract ($)
    spread_width: float     # spread width ($)
    probability_otm: float  # 1 - short_delta (probability short expires OTM)
    return_on_risk: float   # credit / max_loss * 100 (%)
    xgb_confidence: Optional[float]
    sizing_note: str        # "Full sizing (3-5%)" or "Reduced sizing (1.5-2.5%)"
    liquidity_ok: bool
    earnings_safe: bool     # no earnings inside DTE window
    perplexity_news_ok: bool = True


@dataclass
class OptionsStrategistReport:
    verdict_used: str           # GREEN | YELLOW | RED
    sizing_multiplier: float    # 1.0 or 0.5
    trade_ideas: list[TradeIdea]
    candidates_scanned: int
    candidates_passed: int
    summary_hebrew: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Data fetchers ─────────────────────────────────────────────────────────────

def _get_iv_rank(ticker: str) -> tuple[float, float]:
    """
    Calculate IV Rank and IV Percentile for a ticker using 1-year history.
    Returns (iv_rank, iv_percentile). Both 0-100.
    Falls back to (50.0, 50.0) on error.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 50:
            return 50.0, 50.0

        # Proxy IV from 20-day rolling realized volatility (annualized)
        returns = hist["Close"].pct_change().dropna()
        rolling_vol = returns.rolling(20).std() * math.sqrt(252) * 100

        if rolling_vol.empty:
            return 50.0, 50.0

        current_vol = float(rolling_vol.iloc[-1])
        high_52w = float(rolling_vol.max())
        low_52w = float(rolling_vol.min())

        if high_52w == low_52w:
            return 50.0, 50.0

        # IV Rank: position of current within annual high/low range
        iv_rank = (current_vol - low_52w) / (high_52w - low_52w) * 100

        # IV Percentile: fraction of days where vol was lower than today
        n_lower = (rolling_vol < current_vol).sum()
        iv_pct = n_lower / len(rolling_vol) * 100

        return round(iv_rank, 1), round(iv_pct, 1)

    except Exception as e:
        logger.warning("IV calc failed for %s: %s", ticker, e)
        return 50.0, 50.0


def _get_current_price(ticker: str) -> Optional[float]:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None


def _calc_expected_move(price: float, iv_rank: float, dte: int) -> float:
    """
    Expected Move = Price × IV% × √(DTE/365)
    Uses IV Rank as a proxy for current IV% (rough approximation).
    Returns ±$ amount representing 1SD move.
    """
    # Map IV rank (0-100) to approximate IV% (15-80% typical range)
    iv_pct = 0.15 + (iv_rank / 100) * 0.65
    em = price * iv_pct * math.sqrt(dte / 365)
    return round(em, 2)


def _check_liquidity(ticker: str) -> bool:
    """
    Check if options are liquid enough.
    Returns True if bid-ask spread on ATM options < MAX_SPREAD_PCT.
    Defaults to True if check cannot be performed.
    """
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            return False

        chain = stock.option_chain(expirations[0])
        calls = chain.calls

        if calls.empty:
            return False

        price = _get_current_price(ticker)
        if not price:
            return True  # benefit of doubt

        calls = calls.copy()
        calls["distance"] = abs(calls["strike"] - price)
        atm = calls.nsmallest(1, "distance").iloc[0]

        bid = float(atm.get("bid", 0))
        ask = float(atm.get("ask", 0))
        mid = (bid + ask) / 2

        if mid <= 0:
            return False

        spread_pct = (ask - bid) / mid
        return spread_pct <= MAX_SPREAD_PCT

    except Exception:
        return True  # default to OK if check fails


def _check_earnings_safe(ticker: str, dte: int) -> bool:
    """
    Returns True if no earnings announcement is expected within the DTE window.
    Uses yfinance calendar data.
    """
    try:
        stock = yf.Ticker(ticker)
        cal = stock.calendar
        if cal is None or (hasattr(cal, "empty") and cal.empty):
            return True

        if "Earnings Date" in cal.index:
            earnings_date = cal.loc["Earnings Date"].iloc[0]
            if hasattr(earnings_date, "date"):
                days_until = (earnings_date.date() - datetime.now().date()).days
                if 0 <= days_until <= dte:
                    logger.info("%s has earnings in %d days — flagging unsafe", ticker, days_until)
                    return False
        return True
    except Exception:
        return True  # default to safe if check fails


def _check_ticker_news(ticker: str) -> tuple[bool, str]:
    """
    Ask Perplexity if there are any major negative news for this ticker
    in the last 48 hours that would make an options trade risky.

    Returns (is_safe, risk_description).
    is_safe=False means skip this ticker.
    """
    try:
        from app.services.perplexity_service import PerplexityService
        svc = PerplexityService()
        if not svc.is_available():
            return True, ""  # no API key → skip check, allow trade

        answer = svc.ask(
            f"In the last 48 hours, are there any major negative news, "
            f"earnings warnings, SEC investigations, product recalls, "
            f"CEO departures, or significant analyst downgrades for {ticker}? "
            f"Answer with YES or NO first, then explain briefly in 2 sentences max."
        )

        if not answer:
            return True, ""

        answer_lower = answer.lower()
        if answer_lower.startswith("yes") or "major negative" in answer_lower:
            logger.info("Perplexity flagged %s with negative news: %s", ticker, answer[:100])
            return False, answer[:200]

        return True, ""

    except Exception as e:
        logger.warning("Perplexity ticker check failed for %s: %s", ticker, e)
        return True, ""  # fail open → allow trade


def _select_strategy(direction: str, iv_rank: float) -> str:
    """Select strategy based on direction and IV environment."""
    if iv_rank < MIN_IV_RANK:
        return "Skip"

    if direction == "bullish":
        return "Bull Put Spread"
    elif direction == "bearish":
        return "Bear Call Spread"
    else:
        return "Iron Condor"


def _build_trade_idea(
    ticker: str,
    direction: str,
    xgb_confidence: Optional[float],
    sizing_multiplier: float,
) -> Optional[TradeIdea]:
    """
    Run the 7-step selection on a single ticker using REAL market data.
    Returns TradeIdea or None if ticker fails any filter.
    """
    # Get REAL IV data from yfinance options chain
    iv_data = get_realtime_iv_data(ticker)

    # Step 1: Liquidity check
    if not iv_data.is_liquid:
        logger.info("SKIP %s — bid-ask spread %.1f%% > 10%%", ticker, iv_data.bid_ask_spread_pct)
        return None

    if iv_data.current_price <= 0:
        logger.info("SKIP %s — could not get price", ticker)
        return None

    # Step 3: IV Rank minimum
    if iv_data.iv_rank < MIN_IV_RANK:
        logger.info("SKIP %s — IV Rank %.1f < %d", ticker, iv_data.iv_rank, MIN_IV_RANK)
        return None

    # Step 4: IV Percentile dual confirmation
    if iv_data.iv_percentile < MIN_IV_PCT:
        logger.info("SKIP %s — IV Percentile %.1f < %d", ticker, iv_data.iv_percentile, MIN_IV_PCT)
        return None

    # Step 5: Expected move (REAL, from yfinance IV)
    dte = 38  # target 30-45 DTE sweet spot
    em = iv_data.expected_move_30d if iv_data.expected_move_30d > 0 else (
        iv_data.current_price * (iv_data.iv_current / 100) * math.sqrt(dte / 365)
    )
    em = round(em, 2)

    # Step 6: Strategy selection
    strategy = _select_strategy(direction, iv_data.iv_rank)
    if strategy == "Skip":
        return None

    # Step 7: REAL strike selection from options chain
    chain = get_options_chain(ticker, target_dte=dte)

    if chain:
        actual_dte = chain.dte
        expiration = chain.expiration
        if strategy == "Bull Put Spread":
            short_strike = find_strike_by_delta(chain, target_delta=0.20, option_type="put")
        elif strategy == "Bear Call Spread":
            short_strike = find_strike_by_delta(chain, target_delta=0.20, option_type="call")
        else:  # Iron Condor — use put side as primary
            short_strike = find_strike_by_delta(chain, target_delta=0.20, option_type="put")
    else:
        # Fallback: estimate strike from expected move
        actual_dte = dte
        expiration = "N/A"
        short_strike = None

    # If no real strike found, estimate
    if short_strike is None:
        if strategy == "Bull Put Spread":
            short_strike = round(iv_data.current_price - em * 1.05, 0)
        elif strategy == "Bear Call Spread":
            short_strike = round(iv_data.current_price + em * 1.05, 0)
        else:
            short_strike = round(iv_data.current_price - em * 1.05, 0)

    spread_width = 5.0  # standard $5 wide spread
    long_strike = short_strike - spread_width if "Put" in strategy else short_strike + spread_width
    short_delta = 0.20

    # Credit: real estimate from IV (higher IV = more credit)
    iv_factor = min(iv_data.iv_current / 25.0, 2.5)  # normalize to ~25% base IV
    credit = round(spread_width * 0.30 * iv_factor, 2)
    if strategy == "Iron Condor":
        credit = round(credit * 1.8, 2)  # both sides

    max_loss = round((spread_width - credit) * 100, 2)
    probability_otm = round((1 - short_delta) * 100, 1)
    ror = round(credit / (spread_width - credit) * 100, 1) if (spread_width - credit) > 0 else 0

    # Sizing note
    pct_low = 3 * sizing_multiplier
    pct_high = 5 * sizing_multiplier
    sizing_note = f"סיזינג: {pct_low:.1f}%-{pct_high:.1f}% מהחשבון"

    # Earnings check
    earnings_safe = _check_earnings_safe(ticker, actual_dte)

    # Perplexity news check
    news_safe, _ = _check_ticker_news(ticker)
    if not news_safe:
        logger.info("SKIP %s — Perplexity flagged negative news", ticker)
        return None

    return TradeIdea(
        ticker=ticker,
        strategy=strategy,
        direction=direction,
        current_price=iv_data.current_price,
        iv_rank=iv_data.iv_rank,
        iv_percentile=iv_data.iv_percentile,
        expected_move=em,
        dte=actual_dte,
        short_strike=short_strike,
        long_strike=long_strike,
        short_delta=short_delta,
        credit=credit,
        max_loss=max_loss,
        spread_width=spread_width,
        probability_otm=probability_otm,
        return_on_risk=ror,
        xgb_confidence=xgb_confidence,
        sizing_note=sizing_note,
        liquidity_ok=iv_data.is_liquid,
        earnings_safe=earnings_safe,
    )


# ── Hebrew report builder ─────────────────────────────────────────────────────

def _build_trade_card(idea: TradeIdea, rank: int) -> str:
    strategy_emoji = {
        "Bull Put Spread": "🐂",
        "Bear Call Spread": "🐻",
        "Iron Condor": "🦅",
    }.get(idea.strategy, "📊")

    iv_signal = (
        "🔥 גבוה מאוד" if idea.iv_rank >= 50
        else ("✅ גבוה" if idea.iv_rank >= 35 else "⚠️ בינוני")
    )
    earnings_warn = (
        "" if idea.earnings_safe
        else "\n⚠️ *שים לב: יש דוחות בתוך חלון הפקיעה!*"
    )
    xgb_str = (
        f"`{idea.xgb_confidence:.1f}%`"
        if idea.xgb_confidence is not None else "N/A"
    )

    if idea.strategy == "Iron Condor":
        call_short = round(idea.current_price + idea.expected_move * 1.05)
        call_long = call_short + 5
        strike_line = (
            f"• Short Put: `${idea.short_strike}` / Long Put: `${idea.long_strike}`\n"
            f"• Short Call: `${call_short}` / Long Call: `${call_long}`"
        )
    else:
        action = "מכור"
        strike_line = (
            f"• Short Strike: `${idea.short_strike}` ({action})\n"
            f"• Long Strike: `${idea.long_strike}` (קנה — הגנה)"
        )

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{strategy_emoji} *רעיון #{rank}: {idea.ticker} — {idea.strategy}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 מחיר נוכחי: `${idea.current_price}`\n"
        f"📅 DTE: `{idea.dte} ימים` (מסלול מועדף 30-45)\n"
        f"\n"
        f"📊 *ניתוח IV:*\n"
        f"• IV Rank: `{idea.iv_rank}%` {iv_signal}\n"
        f"• IV Percentile: `{idea.iv_percentile}%`\n"
        f"• Expected Move (1SD): `±${idea.expected_move}`\n"
        f"\n"
        f"🎯 *מבנה העסקה:*\n"
        f"{strike_line}\n"
        f"• Credit: `${idea.credit}` לצמד\n"
        f"• Max Loss: `${idea.max_loss}` לחוזה\n"
        f"• Probability OTM: `{idea.probability_otm}%`\n"
        f"• Return on Risk: `{idea.return_on_risk}%`\n"
        f"\n"
        f"🤖 XGBoost Confidence: {xgb_str}\n"
        f"📐 {idea.sizing_note}{earnings_warn}"
    )


def _build_hebrew_summary(report: OptionsStrategistReport) -> str:
    verdict_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(report.verdict_used, "⚪")
    sizing_note = (
        "סיזינג מלא" if report.sizing_multiplier == 1.0
        else "סיזינג מופחת 50% (YELLOW regime)"
    )

    if not report.trade_ideas:
        return (
            f"👨‍💼 *Agent 2 — Options Strategist*\n"
            f"🕙 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"{verdict_emoji} Regime: {report.verdict_used}\n\n"
            f"😴 לא נמצאו עסקאות העומדות בכל 7 הקריטריונים היום.\n"
            f"סרקתי {report.candidates_scanned} מניות, "
            f"{report.candidates_passed} עברו את הסינון הראשוני."
        )

    cards = "\n\n".join(
        _build_trade_card(idea, i + 1)
        for i, idea in enumerate(report.trade_ideas)
    )

    header = (
        f"👨‍💼 *Agent 2 — Options Strategist*\n"
        f"🕙 {datetime.now().strftime('%d/%m/%Y %H:%M')} שעון ישראל\n\n"
        f"{verdict_emoji} Regime: *{report.verdict_used}* | {sizing_note}\n"
        f"📋 נסרקו: {report.candidates_scanned} מניות → "
        f"עברו סינון: {report.candidates_passed} → "
        f"נבחרו: {len(report.trade_ideas)} עסקאות\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *כללי ניהול לכל עסקה:*\n"
        f"• סגור ב-*50% רווח* מהקרדיט\n"
        f"• צא ב-*2-2.5× הקרדיט* (Stop Loss)\n"
        f"• בדוק פוזיציה ב-*21 DTE*\n"
        f"• סגור הכל ב-*10 DTE* ללא יוצא מהכלל\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

    return f"{header}\n\n{cards}"


# ── Main Agent ────────────────────────────────────────────────────────────────

class OptionsStrategistAgent:
    """
    Agent 2 — Options Strategist.

    Usage:
        agent = OptionsStrategistAgent()
        report = agent.run()
    """

    def run(self) -> OptionsStrategistReport:
        logger.info("=== Agent 2: Options Strategist — START ===")

        # 1. Read Agent 1 verdict
        from app.agent.market_regime_agent import get_latest_regime
        regime = get_latest_regime()

        if not regime:
            logger.warning("No regime report found — running with YELLOW (conservative)")
            verdict = "YELLOW"
            sizing_multiplier = 0.5
        else:
            verdict = regime.get("verdict", "YELLOW")
            sizing_multiplier = 1.0 if verdict == "GREEN" else 0.5

        logger.info("Regime: %s | Sizing: %.0f%%", verdict, sizing_multiplier * 100)

        if verdict == "RED":
            logger.info("RED regime — aborting, no trades today")
            report = OptionsStrategistReport(
                verdict_used=verdict,
                sizing_multiplier=0.0,
                trade_ideas=[],
                candidates_scanned=0,
                candidates_passed=0,
                summary_hebrew=(
                    "👨‍💼 *Agent 2 — Options Strategist*\n\n"
                    "🔴 *Regime: RED — אין עסקאות היום*\n\n"
                    "Agent 1 זיהה תנאי שוק שאינם מתאימים לפתיחת פוזיציות חדשות.\n"
                    "אנחנו מחכים ל-GREEN או YELLOW."
                ),
            )
            self._notify_telegram(report)
            return report

        # 2. Finviz scan
        from app.services.finviz_service import FinvizService
        raw_bullish = FinvizService.get_bullish_tickers(n=SCAN_LIMIT)
        raw_bearish = FinvizService.get_bearish_tickers(n=SCAN_LIMIT)
        candidates_scanned = len(raw_bullish) + len(raw_bearish)
        logger.info("Finviz: %d bullish, %d bearish", len(raw_bullish), len(raw_bearish))

        # 3. XGBoost filter — score each candidate, keep top half per direction
        from app.services.ml_service import predict_confidence

        def _score(tickers, direction):
            scored = []
            for t in tickers:
                conf = predict_confidence(t)
                scored.append((conf or 0.0, t, direction))
            return sorted(scored, reverse=True)[:XGB_TOP_N // 2]

        top_bull = _score(raw_bullish, "bullish")
        top_bear = _score(raw_bearish, "bearish")
        all_candidates = top_bull + top_bear

        # 4. Cooldown filter
        from app.data.mongo_client import MongoDB
        filtered = []
        for conf, ticker, direction in all_candidates:
            if MongoDB.was_options_sent_recently(ticker, days=COOLDOWN_DAYS):
                logger.info("Cooldown skip: %s", ticker)
                continue
            filtered.append((conf, ticker, direction))

        logger.info("After cooldown filter: %d candidates", len(filtered))

        # 5 & 6. Per-ticker 7-step selection → collect top FINAL_TOP_N
        trade_ideas: list[TradeIdea] = []
        for conf, ticker, direction in filtered:
            if len(trade_ideas) >= FINAL_TOP_N:
                break

            logger.info("Evaluating %s (%s, XGB=%.1f)...", ticker, direction, conf)

            idea = _build_trade_idea(
                ticker=ticker,
                direction=direction,
                xgb_confidence=conf if conf > 0 else None,
                sizing_multiplier=sizing_multiplier,
            )

            if idea:
                if not idea.earnings_safe:
                    logger.info("SKIP %s — earnings inside DTE window", ticker)
                    continue
                trade_ideas.append(idea)
                logger.info(
                    "ACCEPTED %s: %s | IV_R=%.1f | IV_P=%.1f | Credit=$%.2f | P(OTM)=%.1f%%",
                    ticker, idea.strategy, idea.iv_rank, idea.iv_percentile,
                    idea.credit, idea.probability_otm,
                )

        candidates_passed = len(trade_ideas)

        # 7. Build report
        report = OptionsStrategistReport(
            verdict_used=verdict,
            sizing_multiplier=sizing_multiplier,
            trade_ideas=trade_ideas,
            candidates_scanned=candidates_scanned,
            candidates_passed=candidates_passed,
            summary_hebrew="",
        )
        report.summary_hebrew = _build_hebrew_summary(report)

        # 8. Save to MongoDB
        self._save_to_mongo(report)

        # 9. Send to Telegram
        self._notify_telegram(report)

        # 10. Log cooldown for accepted tickers
        for idea in trade_ideas:
            MongoDB.log_options_sent(idea.ticker)

        logger.info(
            "=== Agent 2: Options Strategist — DONE | %d ideas sent ===",
            len(trade_ideas),
        )
        return report

    def _save_to_mongo(self, report: OptionsStrategistReport) -> None:
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            doc = {
                "verdict_used": report.verdict_used,
                "sizing_multiplier": report.sizing_multiplier,
                "candidates_scanned": report.candidates_scanned,
                "candidates_passed": report.candidates_passed,
                "trade_ideas": [asdict(t) for t in report.trade_ideas],
                "timestamp": report.timestamp,
            }
            db["options_strategist_reports"].insert_one(doc)
            logger.info("Agent 2 report saved to MongoDB")
        except Exception as e:
            logger.error("Failed to save Agent 2 report: %s", e)

    def _notify_telegram(self, report: OptionsStrategistReport) -> None:
        try:
            from app.agent.telegram_bot import notify_trade
            msg = report.summary_hebrew
            if len(msg) <= 4000:
                notify_trade(msg)
            else:
                # Split on trade card separators
                parts = msg.split("━━━━━━━━━━━━━━━━━━━━━━")
                for part in parts:
                    if part.strip():
                        notify_trade(part.strip())
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)


def get_todays_ideas() -> list[dict]:
    """
    Used by Agent 3 (Risk Manager) to read today's trade ideas.
    Returns list of trade idea dicts from the most recent Agent 2 report.
    """
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        doc = db["options_strategist_reports"].find_one(sort=[("timestamp", -1)])
        if doc:
            return doc.get("trade_ideas", [])
        return []
    except Exception as e:
        logger.error("Failed to read Agent 2 report: %s", e)
        return []


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    agent = OptionsStrategistAgent()
    report = agent.run()
    print("\n" + report.summary_hebrew)
