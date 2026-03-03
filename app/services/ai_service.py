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
