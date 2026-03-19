"""
Autonomous Trading Agent — ReAct loop via OpenAI function calling.

No external agent framework needed — the project already uses the OpenAI SDK.
The agent follows the ReAct pattern natively using OpenAI's tool-calling API:

    Reason → call a Tool → Observe result → Reason again → ...

The brain is GPT-4o with a Hedge Fund Manager system prompt.
Each tool wraps one of our existing services so the agent can compose them
in any order it deems fit based on current market conditions.

Typical daily workflow the model discovers autonomously:
  1. get_market_conditions  → VIX, SPX, FRED macro
  2. (if VIX > 30)          → abort_run
  3. scan_bullish_tickers   → ranked candidates
  4. scan_bearish_tickers   → ranked candidates
  5. check_options_cooldown (per ticker)
  6. analyze_ticker (top 2-3 per side)
  7. get_0dte_spx_setup
  8. get_options_setup (per approved ticker)
  9. send_options_report    → if quality ≥ 60
     OR abort_run           → if quality < 60

The loop runs until a terminal tool (send_options_report or abort_run) is
called, or MAX_ITERATIONS is reached as a safety guard.
"""

import json
import logging
from datetime import date
from typing import Any

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from openai import RateLimitError, APIConnectionError, APITimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Agent configuration ─────────────────────────────────────────────────────
AGENT_MODEL     = "gpt-4o"
MAX_ITERATIONS  = 20       # safety cap on the ReAct loop
MIN_QUALITY     = 60       # agent must rate quality ≥ this to send email
MAX_TEMP        = 0.2      # low temperature for deterministic reasoning

_OPENAI_TRANSIENT = (RateLimitError, APIConnectionError, APITimeoutError)
TERMINAL_TOOLS  = {"send_options_report", "abort_run"}


# ══════════════════════════════════════════════════════════════════════════════
# System prompt — the agent's "brain" instructions
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""You are an autonomous Hedge Fund Manager specializing in Tastytrade-style options trading.
Your goal: find the highest-probability credit spread setups each day and send a focused,
actionable report — but ONLY when quality genuinely meets your standards.

━━━ DECISION FRAMEWORK ━━━

Step 1 — ALWAYS call get_market_conditions first.
Step 2 — Abort immediately if VIX > 30 (too volatile for defined-risk credit spreads).
Step 3 — Choose scan directions based on macro regime:
    • HIGH_RATE / ELEVATED (Fed Rate > 3.5%)  → premium is rich, scan both directions aggressively
    • VIX > 20  → widen spreads, use larger spread widths
    • VIX < 15  → credit is thin, raise your quality bar (require quality_score ≥ 70)
Step 4 — Check cooldown for each ticker before analyzing it (skip if in_cooldown = true).
Step 5 — Analyze 2–3 top candidates per direction (not all of them — be selective).
Step 6 — Always call get_0dte_spx_setup once — the SPX 0DTE trade is the report anchor.
Step 7 — Build options setups only for tickers that passed your analysis.
Step 8 — Call send_options_report if quality_score ≥ {MIN_QUALITY}, else abort_run.

━━━ RISK RULES (MANDATORY) ━━━

• Never send if quality_score < {MIN_QUALITY}.
• Skip bearish positions on tickers with short_squeeze_risk = HIGH.
• Minimum for sending: at least one valid 0DTE setup OR two stock spreads.
• The reasoning field in send_options_report must be written in professional Hebrew.
• If a tool returns an error, skip that ticker — do not retry the same call.

━━━ EFFICIENCY RULES ━━━

• Call scan_bullish and scan_bearish with top_n=5 — no more.
• Analyze at most 3 tickers per direction — depth beats breadth.
• Do NOT call analyze_ticker on tickers already in cooldown.
• Do NOT call get_options_setup before analyze_ticker — qualify first.
• Call abort_run or send_options_report to end the session — never loop forever.
"""


# ══════════════════════════════════════════════════════════════════════════════
# Tool schema — OpenAI function calling definitions
# ══════════════════════════════════════════════════════════════════════════════

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_market_conditions",
            "description": (
                "Fetch today's market snapshot: SPX price, VIX, FRED Fed Rate, "
                "CPI YoY, and macro regime label. ALWAYS call this first."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_bullish_tickers",
            "description": (
                "Scan Finviz for bullish momentum stocks (price above all SMAs, "
                "positive daily performance, high relative volume). "
                "Returns tickers ranked by XGBoost confidence score."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max tickers to fetch from Finviz. Default 20, max 40.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Max tickers to return after XGBoost ranking. Default 5, max 10.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_bearish_tickers",
            "description": (
                "Scan Finviz for bearish momentum stocks (price below all SMAs, "
                "negative daily performance, high relative volume). "
                "Returns tickers ranked by XGBoost confidence score."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max tickers to fetch from Finviz. Default 20, max 40.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Max tickers to return after XGBoost ranking. Default 5, max 10.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_options_cooldown",
            "description": (
                "Check if a ticker was already included in an options email in the last 4 days. "
                "Returns {ticker, in_cooldown}. Skip tickers where in_cooldown=true."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL)"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_ticker",
            "description": (
                "Run deep analysis on a ticker: current price, SMA technical signals, "
                "5-year margin trends, balance sheet, FCF growth, P/E, PEG, "
                "short interest, institutional ownership %, short squeeze risk, "
                "and most recent SEC 10-K/10-Q filing date. "
                "Use this to qualify a ticker before building an options setup."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_options_setup",
            "description": (
                "Build a credit spread for a qualified stock ticker. "
                "Bullish direction → Bull Put Spread (sell OTM put, 30-45 DTE, 0.25-0.35 delta). "
                "Bearish direction → Bear Call Spread (sell OTM call, 30-45 DTE, 0.25-0.35 delta). "
                "Returns: strike, expiry, credit collected, delta, IV, max profit, max loss, breakeven."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "direction": {
                        "type": "string",
                        "enum": ["Bullish", "Bearish"],
                        "description": "Trade direction: Bullish = Bull Put Spread, Bearish = Bear Call Spread",
                    },
                },
                "required": ["ticker", "direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_0dte_spx_setup",
            "description": (
                "Build today's 0DTE SPX iron condor using SPY as proxy. "
                "Uses Black-Scholes to find short strikes at 0.10-0.15 delta. "
                "Spread width: $3 (VIX ≤ 20) or $5 (VIX > 20). "
                "Returns: expiry, put spread, call spread, total credit, stop loss, profit target."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_options_report",
            "description": (
                "Compile and email the Daily Options Brief via Resend. "
                "TERMINAL ACTION — the agent stops after calling this. "
                "Only call when quality_score >= 60 and you have at least 1 valid setup. "
                "The reasoning field MUST be written in professional Hebrew."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bullish_tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Approved bullish tickers that have valid options setups",
                    },
                    "bearish_tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Approved bearish tickers that have valid options setups",
                    },
                    "quality_score": {
                        "type": "number",
                        "description": "Your confidence 0-100 in the overall report quality. Must be >= 60.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Hebrew summary: why these setups are high-probability today.",
                    },
                },
                "required": ["bullish_tickers", "bearish_tickers", "quality_score", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "abort_run",
            "description": (
                "Abort today's run — no email will be sent. "
                "TERMINAL ACTION — call when: VIX > 30, quality_score < 60, "
                "no valid setups found, or conditions are otherwise unfavorable."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for aborting. Will be logged.",
                    }
                },
                "required": ["reason"],
            },
        },
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# Tool implementations — wrap existing project services
# ══════════════════════════════════════════════════════════════════════════════

def _tool_get_market_conditions() -> dict:
    from app.services.options_service import OptionsService
    from app.services.api_hub import get_macro_context
    ctx   = OptionsService().get_market_context()
    macro = get_macro_context()
    vix   = ctx["vix"]
    return {
        "spx_price": ctx["spx_price"],
        "vix":       vix,
        "vix_regime": (
            "EXTREME — abort recommended"   if vix > 30 else
            "HIGH — wide spreads"           if vix > 20 else
            "NORMAL — standard approach"    if vix > 15 else
            "LOW — thin credit, raise bar"
        ),
        "macro": {
            "fed_rate":  macro.get("fed_rate", "N/A"),
            "cpi_yoy":   macro.get("cpi_yoy",  "N/A"),
            "regime":    macro.get("regime",   "UNKNOWN"),
            "notes":     macro.get("notes",    ""),
        },
    }


def _tool_scan_bullish(limit: int = 20, top_n: int = 5) -> dict:
    from app.services.finviz_service import FinvizService
    from app.services.ml_service import predict_confidence
    limit = min(int(limit), 40)
    top_n = min(int(top_n), 10)
    raw   = FinvizService.get_bullish_tickers(n=limit)
    scored = sorted(
        [{"ticker": t, "xgb_confidence": predict_confidence(t) or 0.0} for t in raw],
        key=lambda x: x["xgb_confidence"],
        reverse=True,
    )
    return {"direction": "Bullish", "tickers": scored[:top_n], "total_scanned": len(raw)}


def _tool_scan_bearish(limit: int = 20, top_n: int = 5) -> dict:
    from app.services.finviz_service import FinvizService
    from app.services.ml_service import predict_confidence
    limit = min(int(limit), 40)
    top_n = min(int(top_n), 10)
    raw   = FinvizService.get_bearish_tickers(n=limit)
    scored = sorted(
        [{"ticker": t, "xgb_confidence": predict_confidence(t) or 0.0} for t in raw],
        key=lambda x: x["xgb_confidence"],
        reverse=True,
    )
    return {"direction": "Bearish", "tickers": scored[:top_n], "total_scanned": len(raw)}


def _tool_check_cooldown(ticker: str) -> dict:
    from app.data.mongo_client import MongoDB
    return {
        "ticker":      ticker.upper(),
        "in_cooldown": MongoDB.was_options_sent_recently(ticker, days=4),
    }


def _tool_analyze_ticker(ticker: str) -> dict:
    from app.services.financial_service import FinancialAnalyzer
    data = FinancialAnalyzer().analyze(ticker)
    if not data:
        return {"ticker": ticker, "error": "No financial data available"}
    # Return a focused summary — avoid token overflow with the full dict
    return {
        "ticker":             ticker,
        "price":              data.get("current_price"),
        "technical_signal":   data.get("technical_signal"),
        "trend_status":       data.get("trend_status"),
        "volume_ratio":       data.get("volume_ratio"),
        "pe_ratio":           data.get("pe_ratio"),
        "peg_ratio":          data.get("peg_ratio"),
        "debt_to_equity":     data.get("debt_to_equity"),
        "current_ratio":      data.get("current_ratio"),
        "fcf_growth":         data.get("fcf_growth"),
        "net_margin_trend":   data.get("net_margin_5y", [])[:3],
        "gross_margin_trend": data.get("gross_margin_5y", [])[:3],
        "short_ratio":        data.get("short_ratio"),
        "short_pct_float":    data.get("short_pct_float"),
        "inst_pct_held":      data.get("inst_pct_held"),
        "short_squeeze_risk": data.get("short_squeeze_risk"),
        "last_sec_filing":    f"{data.get('last_filing')} ({data.get('last_filing_form')})",
    }


def _tool_get_options_setup(ticker: str, direction: str) -> dict:
    from app.services.options_service import OptionsService
    from app.services.ml_service import predict_confidence
    conf = predict_confidence(ticker)
    opt  = OptionsService().get_stock_option(ticker, direction, confidence=conf)
    if not opt:
        return {
            "ticker":    ticker,
            "direction": direction,
            "error":     "No options data (no listed options or chain too thin)",
        }
    return opt


def _tool_get_0dte_spx() -> dict:
    from app.services.options_service import OptionsService
    svc   = OptionsService()
    ctx   = svc.get_market_context()
    setup = svc.build_0dte_spx_setup(ctx["vix"] or 15.0)
    if not setup:
        return {"error": "Could not build 0DTE setup — options data unavailable"}
    return {**setup, "spy_price": ctx.get("spx_price")}


def _tool_send_options_report(
    bullish_tickers: list,
    bearish_tickers: list,
    quality_score:   float,
    reasoning:       str,
) -> dict:
    """Build the full report payload and send via Resend."""
    quality_score = float(quality_score)
    if quality_score < MIN_QUALITY:
        return {
            "sent":   False,
            "reason": f"quality_score {quality_score:.0f} < minimum {MIN_QUALITY} — email blocked",
        }

    from app.services.options_service import OptionsService
    from app.services.ai_service import AIService
    from app.services.email_service import EmailService
    from app.services.api_hub import get_macro_context
    from app.services.ml_service import predict_confidence
    from app.services.news_scraper import NewsScraper
    from app.data.mongo_client import MongoDB
    import yfinance as yf

    # Build core options report
    svc    = OptionsService()
    report = svc.build_report(
        [t for t in bullish_tickers],
        [t for t in bearish_tickers],
    )
    report["macro_context"] = get_macro_context()

    # Enrich each stock option with news + company context
    scraper = NewsScraper()
    for opt in report.get("stock_options", []):
        t = opt["ticker"]
        opt["confidence"] = predict_confidence(t)
        raw_news = scraper.get_stock_news(t, limit=5)
        opt["news_headlines"] = [n["headline"] for n in raw_news[:3]]
        try:
            info = yf.Ticker(t).info
            name = info.get("shortName", t)
            sec  = info.get("sector", "")
            ind  = info.get("industry", "")
            desc = (info.get("longBusinessSummary") or "")[:300]
            opt["business_summary"] = f"{name} · {sec} · {ind}: {desc}".strip()
        except Exception:
            opt["business_summary"] = ""

    # AI commentary
    ai_svc   = AIService()
    analysis = ai_svc.get_options_analysis(report)

    # Prepend the agent's own reasoning to the SPX analysis block
    if reasoning:
        analysis["spx_analysis"] = (
            f"🤖 סיבת הסוכן לשליחת הדוח היום:\n{reasoning}\n\n"
            + (analysis.get("spx_analysis") or "")
        )

    # Send
    EmailService.send_options_report(report, analysis)

    # Log cooldown
    for opt in report.get("stock_options", []):
        MongoDB.log_options_sent(opt["ticker"])

    n = len(report.get("stock_options", []))
    spx_ok = report.get("spx_setup") is not None
    logger.info(
        "[Agent] Report sent — %d stock spreads, 0DTE: %s, quality: %.0f",
        n, "✓" if spx_ok else "✗", quality_score,
    )

    # Push Telegram notification for each approved trade
    try:
        from app.agent.telegram_bot import notify_trade
        for opt in report.get("stock_options", []):
            t   = opt.get("ticker", "?")
            d   = opt.get("direction", "Bullish")
            cr  = opt.get("credit", 0)
            dlt = opt.get("short_delta", "?")
            iv  = opt.get("iv", "?")
            emoji = "🟢" if d == "Bullish" else "🔴"
            kind  = "Bull Put Spread" if d == "Bullish" else "Bear Call Spread"
            notify_trade(
                f"{emoji} *{t}* — {kind}\n"
                f"קרדיט: `${cr:.2f}` | Delta: `{dlt}` | IV: `{iv}%`"
            )
        if spx_ok:
            spx = report["spx_setup"]
            cr  = spx.get("total_credit", 0)
            notify_trade(
                f"🦅 *SPX 0DTE Iron Condor*\n"
                f"קרדיט כולל: `${cr:.2f}` | "
                f"יעד רווח: `${spx.get('profit_target', 0):.2f}` | "
                f"סטופ: `${spx.get('stop_loss', 0):.2f}`"
            )
    except Exception:
        logger.debug("Telegram trade notification skipped (non-fatal)")

    return {"sent": True, "stocks_included": n, "spx_0dte": spx_ok, "quality_score": quality_score}


def _tool_abort(reason: str) -> dict:
    logger.info("[Agent] Run aborted: %s", reason)
    return {"aborted": True, "reason": reason}


# ── Tool registry — maps function name → callable ─────────────────────────

_REGISTRY: dict[str, Any] = {
    "get_market_conditions": lambda **_:                            _tool_get_market_conditions(),
    "scan_bullish_tickers":  lambda limit=20, top_n=5, **_:        _tool_scan_bullish(limit, top_n),
    "scan_bearish_tickers":  lambda limit=20, top_n=5, **_:        _tool_scan_bearish(limit, top_n),
    "check_options_cooldown": lambda ticker, **_:                   _tool_check_cooldown(ticker),
    "analyze_ticker":        lambda ticker, **_:                    _tool_analyze_ticker(ticker),
    "get_options_setup":     lambda ticker, direction, **_:         _tool_get_options_setup(ticker, direction),
    "get_0dte_spx_setup":    lambda **_:                            _tool_get_0dte_spx(),
    "send_options_report":   lambda bullish_tickers, bearish_tickers,
                                    quality_score, reasoning, **_:
                                    _tool_send_options_report(
                                        bullish_tickers, bearish_tickers,
                                        quality_score, reasoning),
    "abort_run":             lambda reason, **_:                    _tool_abort(reason),
}


# ══════════════════════════════════════════════════════════════════════════════
# The Agent
# ══════════════════════════════════════════════════════════════════════════════

class TradingAgent:
    """
    Autonomous options trading agent.

    Implements the ReAct pattern:
      model_call() → parse tool_calls → execute_tools() → model_call() → ...

    Terminates when the model calls send_options_report or abort_run,
    or when MAX_ITERATIONS is reached.

    Usage:
        agent = TradingAgent()
        summary = agent.run()
        print(summary)
    """

    def __init__(self, client: OpenAI | None = None):
        self._client: OpenAI = client or OpenAI(api_key=settings.OPENAI_API_KEY)
        self._messages: list[dict] = []
        self._iteration: int = 0
        self._tool_call_log: list[dict] = []

    # ── Private helpers ────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(_OPENAI_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
    )
    def _call_model(self, tool_choice: str = "auto"):
        return self._client.chat.completions.create(
            model=AGENT_MODEL,
            messages=self._messages,
            tools=TOOLS,
            tool_choice=tool_choice,
            temperature=MAX_TEMP,
            max_tokens=2000,
        ).choices[0]

    def _execute_tool_calls(self, tool_calls) -> list[dict]:
        """Execute every tool call in the batch; return tool-result messages."""
        result_msgs: list[dict] = []
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            logger.info(
                "[Agent iter=%d] → %s(%s)",
                self._iteration, name,
                json.dumps(args, ensure_ascii=False)[:150],
            )

            try:
                fn     = _REGISTRY.get(name)
                result = fn(**args) if fn else {"error": f"Unknown tool: {name}"}
            except Exception as exc:
                logger.exception("[Agent] Tool %s raised", name)
                result = {"error": str(exc)}

            logger.info(
                "[Agent iter=%d] ← %s: %s",
                self._iteration, name,
                json.dumps(result, ensure_ascii=False, default=str)[:250],
            )

            self._tool_call_log.append({"tool": name, "args": args, "result": result})
            result_msgs.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      json.dumps(result, ensure_ascii=False, default=str),
            })

        return result_msgs

    # ── Public interface ───────────────────────────────────────────────────

    def run(self) -> str:
        """
        Execute the full daily workflow.
        Returns a plain-text summary of what happened.
        """
        today = date.today().strftime("%Y-%m-%d")
        self._messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role":    "user",
                "content": (
                    f"Today is {today}. "
                    "Start your daily options workflow now. "
                    "Begin by checking market conditions, then scan and analyze candidates, "
                    "and conclude by sending a report or aborting based on quality. "
                    f"Minimum quality score to send: {MIN_QUALITY}."
                ),
            },
        ]
        self._iteration      = 0
        self._tool_call_log  = []
        terminal_triggered   = False
        final_summary        = ""

        logger.info("[Agent] ══ Daily workflow started — %s ══", today)

        while self._iteration < MAX_ITERATIONS:
            self._iteration += 1
            logger.info("[Agent] ── Iteration %d / %d ──", self._iteration, MAX_ITERATIONS)

            choice = self._call_model()
            msg    = choice.message

            # Append assistant turn (handles both plain content and tool_calls)
            self._messages.append(msg.model_dump(exclude_none=True))

            # ── Natural stop (model finished reasoning) ────────────────────
            if choice.finish_reason == "stop" or not msg.tool_calls:
                final_summary = msg.content or "Agent completed."
                logger.info("[Agent] Stop signal. Summary: %s", final_summary[:300])
                break

            # ── Execute tool calls ─────────────────────────────────────────
            tool_msgs = self._execute_tool_calls(msg.tool_calls)
            self._messages.extend(tool_msgs)

            # ── Check for terminal tool ────────────────────────────────────
            called_terminals = [
                tc.function.name for tc in msg.tool_calls
                if tc.function.name in TERMINAL_TOOLS
            ]
            if called_terminals:
                terminal_triggered = True
                logger.info("[Agent] Terminal tool called: %s", called_terminals[0])

                # One final model call — no more tools — to produce closing summary
                try:
                    closing = self._call_model(tool_choice="none")
                    final_summary = closing.message.content or str(tool_msgs[0]["content"])
                    self._messages.append(closing.message.model_dump(exclude_none=True))
                except Exception:
                    final_summary = f"Completed via {called_terminals[0]}."

                break

        else:
            final_summary = (
                f"[Agent] Safety limit reached ({MAX_ITERATIONS} iterations). "
                "Check logs for details."
            )
            logger.warning(final_summary)

        # ── Session report ─────────────────────────────────────────────────
        tools_called = [e["tool"] for e in self._tool_call_log]
        logger.info(
            "[Agent] ══ Workflow complete — %d iterations, %d tool calls: %s ══",
            self._iteration,
            len(tools_called),
            " → ".join(tools_called),
        )

        return final_summary

    @property
    def tool_call_log(self) -> list[dict]:
        """Read-only log of every tool call and result from the last run."""
        return list(self._tool_call_log)
