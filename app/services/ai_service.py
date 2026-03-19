"""
AI service for swing-trading analysis using OpenAI.
Produces Hebrew company description and trading plan from ticker, headline, and financials.
"""
import logging
from typing import Any

from openai import OpenAI, RateLimitError, APIConnectionError, APITimeoutError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Response format: Part 1 = company description, Part 2 = analysis (Hebrew)
RESPONSE_SEPARATOR = "|||"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 1800    # expanded for full GS analyst framework
DEFAULT_TEMPERATURE = 0.7
# Full HTML report (daily scan) needs more tokens
FULL_REPORT_MODEL = "gpt-4o"
FULL_REPORT_MAX_TOKENS = 1200

_OPENAI_TRANSIENT = (RateLimitError, APIConnectionError, APITimeoutError)


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe .get for dict or non-dict (returns default if not a dict)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _fmt_fin(v: Any) -> str:
    """Format a raw dollar value to a readable B/M string."""
    try:
        v = float(v)
        if v == 0:
            return "N/A"
        if abs(v) >= 1e9:
            return f"${v / 1e9:.1f}B"
        if abs(v) >= 1e6:
            return f"${v / 1e6:.0f}M"
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_margins(margins: list) -> str:
    """Format a list of margin % values as a trend string (newest → oldest)."""
    if not margins:
        return "N/A"
    return " → ".join(f"{m:.1f}%" for m in margins[:4])


def _build_analysis_prompt(
    ticker: str,
    headline: str,
    financials: dict[str, Any],
) -> str:
    """
    Goldman Sachs Senior Equity Research Analyst prompt.
    Uses enriched financial data (5-year margins, balance sheet, FCF, valuation).
    """
    price       = financials.get("current_price", "N/A")
    mkt_cap     = financials.get("market_cap", 0) or 0
    mkt_cap_str = _fmt_fin(mkt_cap)
    tech_signal = financials.get("technical_signal", "ללא איתות מיוחד")
    trend       = financials.get("trend_status", "ללא מגמה ברורה")
    desc        = (financials.get("description", "") or "")[:500]

    rev = financials.get("revenue") or {}
    ni  = financials.get("net_income") or {}

    # 5-year margin trends
    gm_str = _fmt_margins(financials.get("gross_margin_5y", []))
    om_str = _fmt_margins(financials.get("operating_margin_5y", []))
    nm_str = _fmt_margins(financials.get("net_margin_5y", []))

    # Balance sheet
    dte        = financials.get("debt_to_equity", "N/A")
    curr_ratio = financials.get("current_ratio", "N/A")
    cash_str   = _fmt_fin(financials.get("total_cash", 0))
    debt_str   = _fmt_fin(financials.get("total_debt", 0))

    # FCF
    fcf_list = financials.get("fcf_history", [])
    fcf_str  = " → ".join(_fmt_fin(v) for v in fcf_list[:4]) if fcf_list else "N/A"
    fcf_cagr = financials.get("fcf_growth", "N/A")

    # Valuation
    pe  = financials.get("pe_ratio", "N/A")
    peg = financials.get("peg_ratio", "N/A")

    # Institutional / short-interest (populated by api_hub.get_institutional_data)
    short_ratio   = financials.get("short_ratio",        "N/A")
    short_pct     = financials.get("short_pct_float",    "N/A")
    inst_pct      = financials.get("inst_pct_held",      "N/A")
    squeeze_risk  = financials.get("short_squeeze_risk", "N/A")
    last_filing   = financials.get("last_filing",        "N/A")
    filing_form   = financials.get("last_filing_form",   "N/A")

    return f"""
You are a Senior Equity Research Analyst at Goldman Sachs with 20 years of experience \
covering global equities across technology, healthcare, energy, and financials sectors. \
Write an institutional-grade equity research note in Hebrew.

STOCK: {ticker} | Price: ${price} | Market Cap: {mkt_cap_str}
CATALYST: "{headline}"
TECHNICAL: {tech_signal} | TREND: {trend}
BUSINESS: {desc}

═══ QUANTITATIVE DATA ═══
5-Year Profitability (newest → oldest):
  Gross Margin      : {gm_str}
  Operating Margin  : {om_str}
  Net Margin        : {nm_str}
  Revenue QoQ       : {_safe_get(rev, 'change', 'N/A')}%  |  Net Income QoQ: {_safe_get(ni, 'change', 'N/A')}%

Balance Sheet:
  Debt/Equity       : {dte}  |  Current Ratio: {curr_ratio}
  Total Cash        : {cash_str}  |  Total Debt: {debt_str}

Free Cash Flow (5 years, newest → oldest):
  FCF History       : {fcf_str}
  FCF 3yr CAGR      : {fcf_cagr}%

Valuation vs. Peers:
  P/E               : {pe}  |  PEG: {peg}

Short Interest & Institutional Ownership:
  Short Ratio       : {short_ratio}  |  Short % Float: {short_pct}%
  Institutions Held : {inst_pct}%    |  Short Squeeze Risk: {squeeze_risk}
  Last SEC Filing   : {last_filing} ({filing_form})

═══ OUTPUT — USE EXACTLY THIS FORMAT ═══

PART 1 (max 2 sentences — Hebrew company profile):
[What does {ticker} do and what is its core value proposition?]

{RESPONSE_SEPARATOR}

PART 2 (Goldman Sachs Research Note in Hebrew — use ## section headers):

## מודל עסקי
[Core business model, primary revenue drivers, market position — 2-3 sentences]

## מגמות רווחיות (5 שנים)
[Analyze the margin trend data above. Expanding or contracting? Why? Operational leverage?]

## בריאות המאזן
[D/E ratio context, current ratio, net cash/debt position — is the balance sheet a strength or a risk?]

## תזרים מזומנים חופשי (FCF)
[FCF trend and quality of earnings. FCF conversion rate. Is the business generating real cash?]

## חפיר תחרותי (Moat) — ציון: X/10
[Rate competitive moat 1-10. Justify: pricing power, switching costs, scale advantages, IP, network effects]

## איכות הנהלה
[Infer from capital allocation history, margin trajectory, FCF conversion discipline — 2 sentences]

## הערכת שווי מול עמיתים
[P/E {pe} and PEG {peg} in sector context. Cheap, fair-value, or expensive? % upside/downside to fair value?]

## ריבית שורט וסחיטת שורטים (Short Squeeze)
**סיכון לסחיטה: {squeeze_risk}** | Short Ratio: {short_ratio} | Short % Float: {short_pct}%
[Institutions hold {inst_pct}%. Is a short squeeze realistic? What catalyst would trigger it? Last SEC filing: {last_filing}.]

## תרחישי Bull/Bear | יעד 12 חודש
🐂 **Bull Case (יעד: $[X]):** [Key catalysts for upside — 1-2 sentences]
🐻 **Bear Case (רצפה: $[X]):** [Key downside risks — 1-2 sentences]

## המלצה סופית
**[BUY / HOLD / SELL]** | רמת אמון: **[High/Medium/Low]**
[2-sentence conviction statement explaining the core investment thesis]
"""


def _parse_response(content: str) -> dict[str, str]:
    """Parse OpenAI response into hebrew_desc and analysis."""
    content = (content or "").strip()
    if RESPONSE_SEPARATOR in content:
        parts = content.split(RESPONSE_SEPARATOR, 1)
        return {
            "hebrew_desc": parts[0].strip(),
            "analysis": parts[1].strip(),
        }
    return {
        "hebrew_desc": "תיאור חברה זמין בגוף הניתוח",
        "analysis": content,
    }


def _build_full_report_prompt(
    ticker: str,
    price: float | str,
    score: int,
    reasons: list[str],
    fundamentals: Any,
    news: list[Any],
    company_info: dict[str, Any],
) -> str:
    """Build prompt for full HTML report (daily scan)."""
    company_name = company_info.get("name", ticker)
    industry = company_info.get("industry", "N/A")
    news_str = "\n".join(
        n.get("headline", str(n)) if isinstance(n, dict) else str(n)
        for n in (news or [])
    ) or "אין חדשות משמעותיות לאחרונה."
    reasons_str = ", ".join(reasons) if reasons else "ללא"
    fund_str = fundamentals if isinstance(fundamentals, str) else str(fundamentals or "N/A")
    context = (
        "Potential Early Breakout / Squeeze Setup"
        if "Squeeze" in reasons_str
        else "Technical Setup"
    )

    return f"""
Analyze the stock {ticker} ({company_name}) - {industry}.
Context: {context}.
Current Price: ${price}.
Score: {score}/5.
Technical Reasons: {reasons_str}
Fundamentals Data: {fund_str}
Recent News: {news_str}

Task: Write a professional HTML report in HEBREW.

Sections REQUIRED:
1. 'על החברה' - Brief business description.
2. 'Checklist Table' - HTML Table with rows: נר אחרון, ווליום, RSI, MA20, מצב כללי.
   (CRITICAL: Do NOT include "מגמה חודשית"). Use ✅/❌.
3. 'ניתוח פונדמנטלי' - 2-3 sentences analyzing the financial health/news.
4. 'Trade Plan' - Entry/Exit logic based on the chart.
5. 'שורה תחתונה' - Conclusion.

Style: RTL (Right-to-Left), clean design, professional financial Hebrew.
Return ONLY the HTML code (no markdown code blocks).
"""


def _strip_markdown_code_block(content: str) -> str:
    """Remove ```html ... ``` wrapper if present."""
    if not content:
        return content
    return content.replace("```html", "").replace("```", "").strip()


def _build_options_prompt(report: dict) -> str:
    """
    Tastytrade Senior Options Trader persona prompt.
    Receives the full options report dict and outputs structured Hebrew analysis.
    """
    spx    = report.get("spx_price", "N/A")
    vix    = report.get("vix", "N/A")
    dt     = report.get("scan_date", "today")
    setup  = report.get("spx_setup") or {}
    stocks = report.get("stock_options") or []
    macro  = report.get("macro_context") or {}

    # 0DTE summary
    put_s  = setup.get("put_spread") or {}
    call_s = setup.get("call_spread") or {}
    spy_px = setup.get("spy_price", "N/A")
    total_cr = setup.get("total_credit", "N/A")
    stop   = setup.get("stop_loss", "N/A")
    target = setup.get("profit_target", "N/A")

    def fmt_spread(s: dict, label: str) -> str:
        if not s:
            return f"{label}: לא זמין"
        return (
            f"{label}: Short {s.get('short_strike')} / Long {s.get('long_strike')} | "
            f"קרדיט ${s.get('credit')} | Delta {s.get('short_delta')} | "
            f"Max Loss ${s.get('max_loss')}"
        )

    spx_block = (
        f"SPX (SPY proxy): {spy_px}  |  VIX: {vix}  |  תאריך: {dt}\n"
        f"{fmt_spread(put_s, '🐂 Bull Put Spread')}\n"
        f"{fmt_spread(call_s, '🐻 Bear Call Spread')}\n"
        f"קרדיט כולל: ${total_cr}  |  Stop-Loss: ${stop}  |  Profit Target: ${target}"
    ) if setup else "אין נתוני 0DTE זמינים להיום."

    # Stock options summary — enriched with news + business context
    stock_lines = []
    for opt in stocks:
        iv_pct      = f"{opt.get('iv', 0) * 100:.0f}%" if opt.get("iv") else "N/A"
        news        = opt.get("news_headlines") or []
        news_str    = " | ".join(news[:3]) if news else "אין חדשות אחרונות"
        biz         = (opt.get("business_summary") or "")[:300]
        direction_he = "שורי" if opt["direction"] == "Bullish" else "דובי"
        line = (
            f"\n── {opt['ticker']} ({direction_he}) ──\n"
            f"עסק: {biz or 'N/A'}\n"
            f"אסטרטגיה: {opt['strategy']} | "
            f"Short {opt.get('short_strike')} → Long {opt.get('long_strike')} | "
            f"פקיעה: {opt.get('expiry')} ({opt.get('days')}d)\n"
            f"קרדיט: ${opt.get('credit')} | Max Loss: ${opt.get('max_loss')} | "
            f"Breakeven: {opt.get('breakeven')}\n"
            f"Delta: {opt.get('delta')} | IV: {iv_pct} | XGBoost: {opt.get('confidence', 'N/A')}%\n"
            f"חדשות אחרונות: {news_str}"
        )
        stock_lines.append(line)
    stocks_block = "\n".join(stock_lines) if stock_lines else "אין עסקאות מניות."

    macro_notes = macro.get("notes", "נתוני מאקרו לא זמינים.")
    fed_rate    = macro.get("fed_rate", "N/A")
    cpi_yoy     = macro.get("cpi_yoy",  "N/A")
    macro_regime = macro.get("regime",  "UNKNOWN")

    return f"""You are a senior options trader at Tastytrade with 15 years of experience \
specialising in 0DTE SPX credit spreads and individual stock options.  \
You follow the Tastytrade probability-based approach: sell premium at high IV rank, \
target 0.10–0.15 delta for index spreads, 0.25–0.35 delta for stocks, \
always define risk with a spread, take profits at 50% of max, cut at 2× credit.

TODAY'S MARKET DATA
===================
SPX: {spx}  |  VIX: {vix}  |  Date: {dt}
VIX Regime: {'גבוה — מכרו פרמיה רחבה יותר' if float(vix or 0) > 20 else 'נמוך — מרווחים צרים, אפשר סינגל-לג'}

US MACRO ENVIRONMENT (FRED)
============================
{macro_notes}
Fed Funds Rate: {fed_rate}%  |  CPI YoY: {cpi_yoy}%  |  Macro Regime: {macro_regime}

0DTE SPX IRON CONDOR (SPY PROXY)
==================================
{spx_block}

INDIVIDUAL STOCK OPTIONS
========================
{stocks_block}

OUTPUT INSTRUCTIONS — CRITICAL
================================
Write your entire response in professional financial Hebrew.
Use this EXACT structure, separated by |||:

PART 1 — ניתוח 0DTE SPX (max 220 words):
Explain WHY this iron condor is appropriate today given the VIX level and SPX range.
Incorporate the FRED macro context: how do the current Fed Rate ({fed_rate}%) and CPI ({cpi_yoy}%)
affect options premium levels and the recommended strategy width?
Explain each leg (put spread / call spread) and the entry/exit logic in plain Hebrew.
Rate the setup quality: מעולה / טוב / בינוני / לא מומלץ.

|||

PART 2 — ניתוח מניות (3–4 sentences per stock, in Hebrew):
For each ticker cover ALL of the following:
1. מה החברה עושה — תיאור עסקי קצר בעברית (מודל עסקי, מוצרים/שירותים עיקריים).
2. למה הכיוון — הסבר את הלוגיקה הטכנית (מעל/מתחת SMA, נפח, מומנטום) + חדשות רלוונטיות.
3. למה האסטרטגיה — Bull Put Spread / Bear Call Spread: מה אחוז הסבירות לרווח לפי ה-Delta וה-IV?
4. תוכנית המסחר — כניסה מומלצת, יעד (50% קרדיט), עצירה (2× קרדיט), ביטחון XGBoost.

Output ONLY the Hebrew analysis — no markdown code blocks, no English headers."""


class AIService:
    """OpenAI-based analysis for swing trading (Hebrew output)."""

    def __init__(self, client: OpenAI | None = None):
        self.client: OpenAI | None = client
        if self.client is None and settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set; AI analysis will be unavailable.")

    @retry(
        retry=retry_if_exception_type(_OPENAI_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
    )
    def _call_api(self, **kwargs) -> str:
        """Raw OpenAI call with tenacity retry on transient errors."""
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def analyze_stock(
        self,
        ticker: str,
        headline: str,
        financials: dict[str, Any],
    ) -> dict[str, str]:
        """
        Analyzes the stock as a swing trader (OpenAI) and returns a Hebrew trading plan.
        Returns dict with 'hebrew_desc' (company profile) and 'analysis' (trading plan).
        """
        if not self.client:
            return {
                "hebrew_desc": "שירות AI לא מוגדר",
                "analysis": "נא להגדיר OPENAI_API_KEY בקובץ ההגדרות.",
            }

        prompt = _build_analysis_prompt(ticker, headline, financials)

        try:
            content = self._call_api(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=DEFAULT_TEMPERATURE,
            )
            return _parse_response(content)
        except Exception:
            logger.exception("OpenAI API error during stock analysis for %s", ticker)
            return {
                "hebrew_desc": "שגיאה",
                "analysis": "אירעה תקלה בניתוח ה-AI. אנא בדוק את הלוגים.",
            }

    def get_options_analysis(self, report: dict) -> dict[str, str]:
        """
        Tastytrade options analyst persona.
        Takes the full options report dict (from OptionsService.build_report)
        and returns Hebrew analysis split into:
          - 'spx_analysis'   : 0DTE SPX iron condor rationale
          - 'stock_analysis' : per-stock credit spread explanations
        """
        if not self.client:
            return {
                "spx_analysis":   "שירות AI לא מוגדר.",
                "stock_analysis": "נא להגדיר OPENAI_API_KEY.",
            }

        prompt = _build_options_prompt(report)
        try:
            content = self._call_api(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1600,
                temperature=0.6,
            )
            if RESPONSE_SEPARATOR in content:
                parts = content.split(RESPONSE_SEPARATOR, 1)
                return {
                    "spx_analysis":   parts[0].strip(),
                    "stock_analysis": parts[1].strip(),
                }
            return {"spx_analysis": content.strip(), "stock_analysis": ""}
        except Exception:
            logger.exception("OpenAI options analysis failed")
            return {
                "spx_analysis":   "שגיאה בניתוח 0DTE.",
                "stock_analysis": "שגיאה בניתוח מניות.",
            }

    def analyze_stock_full_report(
        self,
        ticker: str,
        price: float | str,
        score: int,
        reasons: list[str],
        fundamentals: Any,
        news: list[Any],
        company_info: dict[str, Any],
    ) -> str:
        """
        Full HTML report for daily scan (profile + technicals + fundamentals + news).
        Returns a single HTML string for embedding in the daily email report.
        """
        if not self.client:
            return "<p>שירות AI לא מוגדר. נא להגדיר OPENAI_API_KEY.</p>"

        prompt = _build_full_report_prompt(
            ticker, price, score, reasons, fundamentals, news, company_info
        )

        try:
            content = self._call_api(
                model=FULL_REPORT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior technical analyst expert in Hebrew and HTML formatting.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=FULL_REPORT_MAX_TOKENS,
                temperature=DEFAULT_TEMPERATURE,
            )
            return _strip_markdown_code_block(content)
        except Exception:
            logger.exception(
                "OpenAI API error during full report generation for %s", ticker
            )
            return "<p>אירעה תקלה בניתוח ה-AI. אנא בדוק את הלוגים.</p>"
