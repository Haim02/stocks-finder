"""
bull_bear_debate.py — TradingAgents-inspired Bull vs Bear Debate System
=======================================================================

Architecture (adapted from AAAI 2025 TradingAgents paper):
  1. Bull Researcher  → builds bullish thesis from real market data
  2. Bear Researcher  → challenges the bull, builds bearish counter-thesis
  3. Judge (Claude)   → weighs both sides, picks verdict + options strategy
  4. Risk Manager     → applies Tastytrade hard rules, flags violations

All functions are SYNC — call from asyncio.to_thread() in Telegram handlers.
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 600


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    return _client


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class DebateResult:
    ticker: str
    bull_thesis: str
    bull_score: float           # 0-100: bull conviction
    bear_thesis: str
    bear_risk_score: float      # 0-100: severity of bear risks
    verdict: str                # "BULLISH" | "BEARISH" | "NEUTRAL"
    strategy: str               # e.g., "Bull Put Spread"
    reason: str                 # judge reasoning in Hebrew
    confidence: float           # 0-100: judge confidence
    risk_flags: list            # Tastytrade rule violations
    risk_compatible: bool       # True = passes all hard rules
    iv_rank: float = 0.0
    current_price: float = 0.0
    error: Optional[str] = None


# ── Step 0: Context aggregation ───────────────────────────────────────────────

def _build_analyst_context(ticker: str) -> dict:
    """Aggregate IV, price, technicals, news, and regime for debate fuel."""
    ctx: dict = {"ticker": ticker}

    # IV + price from options chain
    try:
        from app.services.realtime_market_data import get_realtime_iv_data
        iv = get_realtime_iv_data(ticker)
        ctx["iv_rank"] = iv.iv_rank
        ctx["iv_percentile"] = iv.iv_percentile
        ctx["price"] = iv.current_price
        ctx["expected_move"] = iv.expected_move_30d
    except Exception as e:
        logger.warning("IV fetch failed for %s: %s", ticker, e)
        ctx.update({"iv_rank": 50.0, "iv_percentile": 50.0, "price": 0.0, "expected_move": 0.0})

    # Real-time news via Perplexity
    try:
        from app.services.perplexity_service import PerplexityService
        svc = PerplexityService()
        if svc.is_available():
            ctx["news"] = svc.get_stock_news(ticker)
            ctx["analysts"] = svc.get_analyst_changes(ticker)
        else:
            ctx["news"] = ctx["analysts"] = ""
    except Exception as e:
        logger.warning("Perplexity context failed for %s: %s", ticker, e)
        ctx["news"] = ctx["analysts"] = ""

    # Technicals from smart scanner
    try:
        from app.services.smart_scanner import deep_scan_ticker
        scan = deep_scan_ticker(ticker, fetch_perplexity=False)
        if scan:
            ctx["rsi"] = scan.get("rsi", 50)
            ctx["trend"] = scan.get("trend", "unknown")
            ctx["score"] = scan.get("score", 50)
            ctx["above_ma50"] = scan.get("above_ma50", False)
            ctx["above_ma200"] = scan.get("above_ma200", False)
            ctx["volume_ratio"] = scan.get("volume_ratio", 1.0)
    except Exception as e:
        logger.warning("Smart scanner context failed for %s: %s", ticker, e)

    # Market regime from Agent 1
    try:
        from app.data.mongo_client import MongoDB
        db = MongoDB.get_db()
        doc = db["market_regime_reports"].find_one(sort=[("timestamp", -1)])
        ctx["regime"] = doc.get("verdict", "YELLOW") if doc else "YELLOW"
        ctx["regime_reason"] = doc.get("reason_hebrew", "") if doc else ""
    except Exception:
        ctx["regime"] = "YELLOW"
        ctx["regime_reason"] = ""

    return ctx


def _ctx_to_text(ctx: dict) -> str:
    """Serialize context dict to a prompt-ready text block."""
    lines = [
        f"Stock: {ctx['ticker']}",
        f"Price: ${ctx.get('price', 0):.2f}",
        f"IV Rank: {ctx.get('iv_rank', 50):.1f}%",
        f"IV Percentile: {ctx.get('iv_percentile', 50):.1f}%",
        f"Expected Move (30d): ${ctx.get('expected_move', 0):.2f}",
        f"RSI(14): {ctx.get('rsi', 50):.1f}",
        f"Trend: {ctx.get('trend', 'unknown')}",
        f"Smart Score: {ctx.get('score', 50):.0f}/100",
        f"Above MA50: {ctx.get('above_ma50', False)}",
        f"Above MA200: {ctx.get('above_ma200', False)}",
        f"Volume Ratio: {ctx.get('volume_ratio', 1.0):.1f}x",
        f"Market Regime: {ctx.get('regime', 'YELLOW')}",
    ]
    if ctx.get("news"):
        lines.append(f"Latest News: {ctx['news'][:300]}")
    if ctx.get("analysts"):
        lines.append(f"Analyst Changes: {ctx['analysts'][:200]}")
    return "\n".join(lines)


# ── Step 1: Bull Researcher ───────────────────────────────────────────────────

def _run_bull_researcher(ctx: dict) -> tuple:
    """Build the strongest bullish thesis. Returns (thesis: str, conviction: float)."""
    try:
        prompt = (
            f"You are a bullish stock analyst. Build the strongest possible bull case.\n\n"
            f"{_ctx_to_text(ctx)}\n\n"
            f"Write a concise bullish thesis (3-4 sentences):\n"
            f"1. Strongest technical or fundamental reason to be bullish\n"
            f"2. Why IV levels support a bullish options entry\n"
            f"3. Most likely upside catalyst in the next 30-45 days\n\n"
            f"End with: CONVICTION: [0-100]\n"
            f"(80+ = strong, 50-79 = moderate, <50 = weak bull case)"
        )
        resp = _get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        score = 60.0
        m = re.search(r"CONVICTION:\s*(\d+)", text)
        if m:
            score = min(100.0, float(m.group(1)))
            text = text[: text.rfind("CONVICTION:")].strip()
        return text, score
    except Exception as e:
        logger.warning("Bull researcher failed: %s", e)
        return "אין מספיק נתונים לבנות תיזה שורית.", 50.0


# ── Step 2: Bear Researcher ───────────────────────────────────────────────────

def _run_bear_researcher(ctx: dict, bull_thesis: str) -> tuple:
    """Challenge the bull thesis. Returns (bear_thesis: str, risk_score: float)."""
    try:
        prompt = (
            f"You are a bearish stock analyst. Challenge the bull case.\n\n"
            f"{_ctx_to_text(ctx)}\n\n"
            f'Bull analyst said: "{bull_thesis}"\n\n'
            f"Write a concise bearish counter-thesis (3-4 sentences):\n"
            f"1. Biggest weakness or flaw in the bull thesis\n"
            f"2. Technical or fundamental reasons to be cautious\n"
            f"3. Most likely scenario where this trade loses money\n\n"
            f"End with: RISK_SCORE: [0-100]\n"
            f"(80+ = very bearish/high risk, 50-79 = moderate risk, <50 = bull case likely wins)"
        )
        resp = _get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        score = 40.0
        m = re.search(r"RISK_SCORE:\s*(\d+)", text)
        if m:
            score = min(100.0, float(m.group(1)))
            text = text[: text.rfind("RISK_SCORE:")].strip()
        return text, score
    except Exception as e:
        logger.warning("Bear researcher failed: %s", e)
        return "ניתוח הדאונסייד לא זמין כרגע.", 50.0


# ── Step 3: Judge ─────────────────────────────────────────────────────────────

def _run_judge(
    ctx: dict,
    bull_thesis: str,
    bull_score: float,
    bear_thesis: str,
    bear_score: float,
) -> tuple:
    """Weigh both sides. Returns (verdict, strategy, reason_hebrew, confidence)."""
    try:
        iv_rank = ctx.get("iv_rank", 50)
        if iv_rank >= 35:
            iv_env = "HIGH IV (≥35) — sell premium preferred (Iron Condor, Bull Put Spread, Bear Call Spread)"
        elif iv_rank >= 25:
            iv_env = "MODERATE IV (25-35) — spreads viable in both directions"
        else:
            iv_env = "LOW IV (<25) — buy debit preferred (Bull Call Spread, LEAPs, Long Straddle)"

        prompt = (
            f"You are a senior options trading judge. Weigh the Bull vs Bear debate.\n\n"
            f"{_ctx_to_text(ctx)}\n"
            f"IV Environment: {iv_env}\n\n"
            f"BULL CASE (conviction: {bull_score:.0f}/100):\n{bull_thesis}\n\n"
            f"BEAR CASE (risk score: {bear_score:.0f}/100):\n{bear_thesis}\n\n"
            f"Decide:\n"
            f"- VERDICT: BULLISH, BEARISH, or NEUTRAL\n"
            f"- STRATEGY: Exactly one of: Bull Put Spread, Bear Call Spread, Iron Condor, "
            f"Long Straddle, Bull Call Spread, Bear Put Spread\n"
            f"  Rules: BULLISH+IV≥35→Bull Put Spread | BEARISH+IV≥35→Bear Call Spread | "
            f"NEUTRAL+IV≥35→Iron Condor | BULLISH+IV<25→Bull Call Spread | any+IV<25→Long Straddle\n"
            f"- REASON_HEBREW: 2 sentences in Hebrew explaining the decision (keep financial terms in English)\n"
            f"- CONFIDENCE: 0-100\n\n"
            f"Reply in EXACTLY this format:\n"
            f"VERDICT: [BULLISH/BEARISH/NEUTRAL]\n"
            f"STRATEGY: [exact strategy name]\n"
            f"REASON_HEBREW: [Hebrew text]\n"
            f"CONFIDENCE: [number]"
        )
        resp = _get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        verdict, strategy, reason, confidence = "NEUTRAL", "Iron Condor", "המערכת לא הגיעה להחלטה.", 50.0

        for line in text.splitlines():
            if line.startswith("VERDICT:"):
                v = line.replace("VERDICT:", "").strip().upper()
                if v in ("BULLISH", "BEARISH", "NEUTRAL"):
                    verdict = v
            elif line.startswith("STRATEGY:"):
                strategy = line.replace("STRATEGY:", "").strip()
            elif line.startswith("REASON_HEBREW:"):
                reason = line.replace("REASON_HEBREW:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                m = re.search(r"\d+", line)
                if m:
                    confidence = min(100.0, float(m.group()))

        return verdict, strategy, reason, confidence
    except Exception as e:
        logger.warning("Judge failed: %s", e)
        return "NEUTRAL", "Iron Condor", "שגיאה בהפעלת השופט.", 50.0


# ── Step 4: Risk Manager ──────────────────────────────────────────────────────

def _run_risk_manager(ctx: dict, strategy: str, confidence: float) -> tuple:
    """Apply Tastytrade hard rules. Returns (flags: list, compatible: bool)."""
    flags = []
    iv_rank = ctx.get("iv_rank", 50)
    regime = ctx.get("regime", "YELLOW")

    # No naked options — always defined-risk
    if strategy.lower() in ("naked call", "naked put", "short call", "short put"):
        flags.append("❌ Naked options אסור — נדרש defined-risk spread תמיד")

    # IV alignment
    sell_strategies = {"Bull Put Spread", "Bear Call Spread", "Iron Condor"}
    buy_strategies = {"Long Straddle", "Bull Call Spread", "Bear Put Spread"}

    if iv_rank >= 35 and strategy in buy_strategies:
        flags.append(f"⚠️ IV Rank {iv_rank:.0f}% גבוה — עדיף למכור premium, לא לקנות")
    elif iv_rank < 25 and strategy in sell_strategies:
        flags.append(f"⚠️ IV Rank {iv_rank:.0f}% נמוך מדי למכירת Premium — שקול debit spread")

    # Regime gate
    if regime == "RED":
        flags.append("🚫 RED Regime — Agent 1 חסם כניסות חדשות. שוק בסיכון גבוה")

    # Low confidence warning
    if confidence < 55:
        flags.append(f"⚠️ Confidence נמוך ({confidence:.0f}%) — הדיון לא חד משמעי, צמצם סייז")

    hard_violations = sum(1 for f in flags if f.startswith("❌") or f.startswith("🚫"))
    return flags, hard_violations == 0


# ── Public API ────────────────────────────────────────────────────────────────

def run_bull_bear_debate(ticker: str) -> DebateResult:
    """Orchestrate the full 4-step Bull vs Bear debate pipeline."""
    ticker = ticker.upper().strip()
    try:
        ctx = _build_analyst_context(ticker)
        bull_thesis, bull_score = _run_bull_researcher(ctx)
        bear_thesis, bear_score = _run_bear_researcher(ctx, bull_thesis)
        verdict, strategy, reason, confidence = _run_judge(
            ctx, bull_thesis, bull_score, bear_thesis, bear_score
        )
        risk_flags, risk_compatible = _run_risk_manager(ctx, strategy, confidence)

        return DebateResult(
            ticker=ticker,
            bull_thesis=bull_thesis,
            bull_score=bull_score,
            bear_thesis=bear_thesis,
            bear_risk_score=bear_score,
            verdict=verdict,
            strategy=strategy,
            reason=reason,
            confidence=confidence,
            risk_flags=risk_flags,
            risk_compatible=risk_compatible,
            iv_rank=ctx.get("iv_rank", 0.0),
            current_price=ctx.get("price", 0.0),
        )
    except Exception as e:
        logger.exception("run_bull_bear_debate failed for %s", ticker)
        return DebateResult(
            ticker=ticker,
            bull_thesis="", bull_score=0,
            bear_thesis="", bear_risk_score=0,
            verdict="NEUTRAL", strategy="N/A",
            reason="", confidence=0,
            risk_flags=[], risk_compatible=False,
            error=str(e),
        )


def format_debate_hebrew(result: DebateResult) -> str:
    """Format DebateResult as a Hebrew Telegram message."""
    if result.error:
        return f"❌ שגיאה בדיון עבור {result.ticker}: {result.error}"

    verdict_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}.get(result.verdict, "⚪")
    verdict_heb = {"BULLISH": "שורי", "BEARISH": "דובי", "NEUTRAL": "נייטרל"}.get(result.verdict, result.verdict)
    risk_badge = "✅ מאושר" if result.risk_compatible else "⚠️ יש סייגים"

    lines = [
        f"⚔️ *Bull vs Bear Debate — {result.ticker}*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 מחיר: ${result.current_price:.2f} | IV Rank: {result.iv_rank:.0f}%",
        "",
        f"🐂 *Bull Case* (Conviction: {result.bull_score:.0f}/100)",
        result.bull_thesis,
        "",
        f"🐻 *Bear Case* (Risk Score: {result.bear_risk_score:.0f}/100)",
        result.bear_thesis,
        "",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"⚖️ *פסיקת השופט:*",
        f"{verdict_emoji} Verdict: *{verdict_heb}* | Confidence: {result.confidence:.0f}%",
        f"📋 Strategy: *{result.strategy}*",
        f"💭 {result.reason}",
        "",
    ]

    if result.risk_flags:
        lines.append(f"🛡️ *Risk Manager ({risk_badge}):*")
        for flag in result.risk_flags:
            lines.append(f"  {flag}")
    else:
        lines.append("🛡️ Risk Manager: ✅ עובר את כל כללי Tastytrade")

    return "\n".join(lines)
