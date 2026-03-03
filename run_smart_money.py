"""
Smart Money / Institutional Accumulation scanner.

Entry point: python run_smart_money.py

Detects stocks with Wyckoff quiet accumulation patterns:
  - OBV divergence (rising OBV while price is flat/falling)
  - Volatility squeeze (low ATR / range contraction)
  - Volume dry-up (sellers exhausted)
  - Institutional ownership concentration (gorillas)

Stocks scoring ≥ 75 are sent in a Hebrew-formatted email via Resend.
"""

import logging

import resend

from app.core.config import settings
from app.data.mongo_client import MongoDB
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.ml_service import predict_confidence
from app.services.smart_money_service import SmartMoneyService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY

# Macro context from recent Q4 hedge-fund reports ("Great Divergence").
# Used to enrich the AI prompt when a detected ticker is known.
HEDGE_FUND_INSIGHTS: dict[str, str] = {
    "INTC": "Nvidia is aggressively buying Intel to vertically integrate AI fab capacity (allocating over 60% of their portfolio).",
    "SNPS": "High institutional accumulation for AI design software (Nvidia's 2nd largest position).",
    "CRWV": "Massive capital shift towards AI physical infrastructure and cloud data centers.",
    "TEVA": "Defensive/Turnaround consensus among major funds accumulating shares quietly.",
    "RKT": "Hidden consensus uniting value and activist investors playing the housing market recovery.",
    "OXY": "Defensive energy shift favored by institutional giants like Buffett.",
    "BABA": "Bold contrarian play by Tepper on Chinese markets.",
    "META": "Ackman's major bet on AI monetization moving to social media networks.",
}


def send_hebrew_smart_money_email(
    picks: list[dict],
    ai_results: dict[str, dict],
    confidence_map: dict[str, float | None] | None = None,
):
    """Builds and sends the Hebrew-formatted Smart Money HTML email."""
    if not picks:
        return

    subject = f"🦅 דוח כסף חכם: אותרו {len(picks)} מניות באיסוף מוסדי"

    html_body = (
        '<div dir="rtl" style="font-family:\'Segoe UI\',Arial,sans-serif;'
        "max-width:750px;margin:0 auto;background-color:#f4f6f8;padding:20px;\">"
        '<h2 style="background:linear-gradient(90deg,#000428,#004e92);color:white;'
        'padding:20px;border-radius:8px;text-align:center;">'
        "🦅 דוח איסוף מוסדי (Smart Money)</h2>"
    )

    for pick in picks:
        ticker = pick.get("ticker", "N/A")
        tech = pick.get("technicals", {})
        fund = pick.get("fundamentals", {})
        fin = pick.get("full_financials", {})
        ai_data = ai_results.get(ticker, {})

        rev = fin.get("revenue", {})
        ni = fin.get("net_income", {})
        eff = fin.get("efficiency", {})

        score = pick.get("score", 0)
        score_color = "#27ae60" if score > 85 else "#f39c12"

        confidence = (confidence_map or {}).get(ticker)
        if confidence is not None:
            conf_color = "#27ae60" if confidence >= 60 else ("#f39c12" if confidence >= 40 else "#c0392b")
            conf_badge = (
                f'<div style="background-color:{conf_color};color:white;padding:5px 12px;'
                f'border-radius:20px;font-weight:bold;font-size:13px;">'
                f'ביטחון: {confidence}%</div>'
            )
        else:
            conf_badge = ""

        eff_curr = eff.get("curr")
        eff_prev = eff.get("prev")
        eff_display = "-"
        eff_color = "black"
        if isinstance(eff_curr, (int, float)) and isinstance(eff_prev, (int, float)):
            if eff_curr < eff_prev:
                eff_display = "✅ שיפור (התייעלות)"
                eff_color = "green"
            elif eff_curr > eff_prev:
                eff_display = "⚠️ הרעה (בזבזנות)"
                eff_color = "red"

        obv_div  = "✅ כן" if tech.get("obv_divergence") else "❌ לא"
        squeeze  = "✅ פעיל" if tech.get("is_squeeze") else "❌ לא"
        breakout = tech.get("breakout_signal") or "—"
        shakeout = tech.get("shakeout_signal") or "—"
        vbottom  = tech.get("vbottom_signal") or "—"
        inst_own = fund.get("institutional_ownership", "N/A")
        gorillas_str = ", ".join(fund.get("gorillas", [])) or "ללא שינוי חריג"
        reasons_html = "".join(f"<li>{r}</li>" for r in pick.get("reasons", []))

        html_body += f"""
        <div style="background-color:white;border-radius:12px;padding:25px;margin-bottom:30px;box-shadow:0 4px 6px rgba(0,0,0,0.05);">
            <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #eee;padding-bottom:10px;margin-bottom:15px;">
                <div>
                    <h1 style="margin:0;color:#2c3e50;font-size:28px;">{ticker}</h1>
                    <span style="font-size:14px;color:#555;">מחיר: ${fin.get('current_price', 'N/A')}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                    {conf_badge}
                    <div style="background-color:{score_color};color:white;padding:5px 15px;border-radius:20px;font-weight:bold;">
                        ציון: {score}
                    </div>
                </div>
            </div>

            <div style="margin-bottom:20px;">
                <b style="color:#c0392b;">🎯 למה המערכת זיהתה?</b>
                <ul style="margin-top:5px;color:#555;padding-right:20px;">{reasons_html}</ul>
            </div>

            <div style="background:#f8f9fa;padding:12px;border-radius:6px;margin-bottom:15px;font-size:14px;line-height:1.5;">
                <b>🏢 פרופיל חברה:</b> {ai_data.get('hebrew_desc', 'עיבוד נתונים...')}
            </div>

            <div style="background:#e3f2fd;padding:15px;border-radius:8px;margin-bottom:20px;border-right:4px solid #1565c0;">
                <b style="color:#1565c0;">💡 ניתוח AI (אסטרטגיית מוסדיים):</b>
                <div style="margin-top:5px;font-size:14px;line-height:1.5;">{ai_data.get('analysis', '...')}</div>
            </div>

            <div style="display:flex;gap:15px;flex-wrap:wrap;margin-bottom:20px;">
                <div style="flex:1;background:#eafaf1;padding:10px;border-radius:8px;font-size:13px;">
                    <b style="color:#27ae60;">📈 Wyckoff Setup</b><br>
                    סטיית OBV: <b>{obv_div}</b><br>
                    Squeeze: <b>{squeeze}</b><br>
                    פריצה טכנית: <b>{breakout}</b><br>
                    Shakeout Reversal: <b>{shakeout}</b><br>
                    זיהוי היפוך מהיר (Shakeout): <b>{vbottom}</b>
                </div>
                <div style="flex:1;background:#ebf5fb;padding:10px;border-radius:8px;font-size:13px;">
                    <b style="color:#2980b9;">🦍 נתוני מוסדיים</b><br>
                    בעלות מוסדית: <b>{inst_own}%</b><br>
                    שחקנים: <b>{gorillas_str}</b>
                </div>
            </div>

            <h3 style="font-size:16px;border-bottom:1px solid #eee;">📊 דוחות כספיים (השוואה רבעונית)</h3>
            <table style="width:100%;border-collapse:collapse;font-size:14px;text-align:right;">
                <tr style="background:#eee;">
                    <th style="padding:8px;">נתון</th><th style="padding:8px;">נוכחי</th>
                    <th style="padding:8px;">קודם</th><th style="padding:8px;">שינוי</th>
                </tr>
                <tr style="border-bottom:1px solid #eee;">
                    <td style="padding:8px;">הכנסות</td>
                    <td style="padding:8px;">{EmailService.format_number(rev.get('curr', 0))}</td>
                    <td style="padding:8px;">{EmailService.format_number(rev.get('prev', 0))}</td>
                    <td style="padding:8px;color:{'green' if rev.get('change', 0) > 0 else 'red'}">{rev.get('change', 0)}%</td>
                </tr>
                <tr style="border-bottom:1px solid #eee;">
                    <td style="padding:8px;">רווח נקי</td>
                    <td style="padding:8px;">{EmailService.format_number(ni.get('curr', 0))}</td>
                    <td style="padding:8px;">{EmailService.format_number(ni.get('prev', 0))}</td>
                    <td style="padding:8px;color:{'green' if ni.get('change', 0) > 0 else 'red'}">{ni.get('change', 0)}%</td>
                </tr>
                <tr>
                    <td style="padding:8px;"><b>יחס הוצאות</b></td>
                    <td style="padding:8px;">{eff_curr}%</td>
                    <td style="padding:8px;">{eff_prev}%</td>
                    <td style="padding:8px;color:{eff_color};font-weight:bold;">{eff_display}</td>
                </tr>
            </table>

            <div style="text-align:center;margin-top:20px;">
                <a href="https://stockgrid.io/darkpools/{ticker}"
                   style="background-color:#34495e;color:white;text-decoration:none;padding:10px 20px;border-radius:5px;font-size:14px;">
                    צפה בנתוני Dark Pools ➜
                </a>
            </div>
        </div>
        """

    html_body += "</div>"

    try:
        resend.Emails.send(
            {
                "from": settings.FROM_EMAIL,
                "to": [settings.ALERT_TO_EMAIL],
                "subject": subject,
                "html": html_body,
            }
        )
        logger.info("Hebrew Smart Money email sent successfully.")
    except Exception:
        logger.exception("Failed to send Smart Money email")


def run_smart_money_tracker():
    logger.info("Starting Smart Money tracker (Wyckoff + Institutional)...")

    tracker = SmartMoneyService()
    ai_service = AIService()

    # 1. Scan
    results = tracker.run_scan()
    if not results:
        logger.info("No qualifying stocks found today.")
        return

    # 2. XGBoost confidence scores
    logger.info("Computing XGBoost confidence scores...")
    confidence_map: dict[str, float | None] = {}
    for pick in results:
        ticker = pick.get("ticker")
        confidence_map[ticker] = predict_confidence(ticker)
        conf_val = confidence_map[ticker]
        logger.info(
            "Confidence %s: %s%%",
            ticker,
            f"{conf_val:.1f}" if conf_val is not None else "N/A",
        )

    # 3. AI analysis for each pick
    logger.info("Running AI analysis on %d picks...", len(results))
    ai_results_map: dict[str, dict] = {}

    for pick in results:
        ticker = pick.get("ticker")
        score = pick.get("score", 0)
        reasons_str = ", ".join(pick.get("reasons", []))
        conf = confidence_map.get(ticker)
        conf_str = f"{conf:.1f}%" if conf is not None else "N/A (model not trained yet)"

        prompt = (
            f"Institutional Accumulation Detected. Score: {score}. "
            f"Technical & Wyckoff Signals: {reasons_str}. "
            f"XGBoost Historical Confidence Score: {conf_str} "
            f"(probability of ≥5% gain within 10 trading days based on historical patterns). "
            "Explain why institutions may be quietly accumulating this stock."
        )

        special_insight = HEDGE_FUND_INSIGHTS.get(ticker, "")
        if special_insight:
            logger.info("Injecting hedge fund context for %s", ticker)
            prompt += (
                f" MAJOR CONTEXT (Q4 hedge fund data): {special_insight}. "
                "Analyze how this aligns with current financials and technical setup."
            )
        else:
            prompt += (
                " Also consider potential links to AI infrastructure, data centers, "
                "or strategic macro turnaround themes."
            )

        ai_results_map[ticker] = ai_service.analyze_stock(
            ticker, prompt, pick.get("full_financials", {})
        )

    # 4. Send email
    send_hebrew_smart_money_email(results, ai_results_map, confidence_map)
    logger.info("Smart Money scan complete.")


if __name__ == "__main__":
    run_smart_money_tracker()
