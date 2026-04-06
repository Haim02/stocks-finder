"""
Market Regime Classifier — inspired by Citadel morning regime report.
Classifies the current market into GREEN/YELLOW/RED for options selling.

Pulls real-time data: VIX, SPX, futures, put-call ratio, breadth.
Cross-references with MongoDB training_events to detect patterns.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)


def classify_regime() -> dict:
    """
    Full market regime classification.
    Returns dict with regime, score, signals, and strategy recommendation.
    """
    signals = {}
    score   = 0.0   # accumulates weighted sub-scores

    # ── 1. VIX Level ─────────────────────────────────────────────────────
    try:
        vix_price = float(yf.Ticker("^VIX").fast_info.last_price or 20.0)
        if vix_price < 15:
            vix_regime = "נמוך"
            vix_score  = 60
            vix_note   = "מכירת פרמיה בטוחה — שוק רגוע"
        elif vix_price < 20:
            vix_regime = "נורמלי"
            vix_score  = 75
            vix_note   = "סביבה אידיאלית למוכרי פרמיה"
        elif vix_price < 30:
            vix_regime = "מוגבר"
            vix_score  = 85
            vix_note   = "פרמיה שמנה — מכור בזהירות"
        else:
            vix_regime = "משבר"
            vix_score  = 20
            vix_note   = "אל תמכור פרמיה! שוק בחרדיות"
        score += vix_score * 0.30
        signals["vix"] = {
            "value":  round(vix_price, 2),
            "regime": vix_regime,
            "note":   vix_note,
            "score":  vix_score,
        }
    except Exception:
        signals["vix"] = {"value": 20, "regime": "לא זמין", "note": "", "score": 50}
        score += 50 * 0.30

    # ── 2. VIX Term Structure (Contango vs Backwardation) ─────────────────
    try:
        vix_spot = signals["vix"]["value"]
        vix3m    = float(yf.Ticker("^VIX3M").fast_info.last_price or 0)
        if vix3m > 0:
            if vix_spot < vix3m:
                ts_signal = "קונטנגו (נורמלי ✅)"
                ts_score  = 80
                ts_note   = "עקום עולה — סביבה טובה למוכרים"
            else:
                ts_signal = "בקוורדיישן (אזהרה ⚠️)"
                ts_score  = 30
                ts_note   = "עקום הפוך — סיכון גבוה, צמצם חשיפה"
        else:
            ts_signal = "לא זמין"
            ts_score  = 50
            ts_note   = ""
        score += ts_score * 0.15
        signals["term_structure"] = {"signal": ts_signal, "note": ts_note, "score": ts_score}
    except Exception:
        score += 50 * 0.15

    # ── 3. SPX Trend (Range-bound vs Trending) ────────────────────────────
    try:
        spx   = yf.Ticker("^GSPC")
        hist  = spx.history(period="1mo")
        if len(hist) >= 20:
            close    = hist["Close"]
            ma20     = close.rolling(20).mean().iloc[-1]
            price    = close.iloc[-1]
            atr      = (hist["High"] - hist["Low"]).rolling(14).mean().iloc[-1]
            atr_pct  = atr / price * 100

            if atr_pct < 0.8 and abs(price - ma20) / ma20 < 0.02:
                trend_signal = "דשדוש (אידיאלי ✅)"
                trend_score  = 90
                trend_note   = "טווח צר — Iron Condor/Spreads מצוינים"
            elif atr_pct > 2.0:
                trend_signal = "מגמה חזקה (הימנע ❌)"
                trend_score  = 25
                trend_note   = "תנועה חדה — אל תמכור Iron Condor"
            else:
                trend_signal = "מגמה מתונה (זהירות 🟡)"
                trend_score  = 55
                trend_note   = "Credit spreads צרים בלבד"

            spx_price = round(float(price), 2)
        else:
            trend_signal, trend_score, trend_note, spx_price = "לא זמין", 50, "", 0

        score += trend_score * 0.20
        signals["trend"] = {
            "signal":    trend_signal,
            "note":      trend_note,
            "spx_price": spx_price,
            "score":     trend_score,
        }
    except Exception:
        score += 50 * 0.20

    # ── 4. Realized vs Implied Volatility ─────────────────────────────────
    try:
        spy  = yf.Ticker("SPY")
        h    = spy.history(period="1mo")
        if len(h) >= 20:
            rets      = np.log(h["Close"] / h["Close"].shift(1)).dropna()
            rv20      = float(rets.iloc[-20:].std() * np.sqrt(252) * 100)
            iv_spx    = signals["vix"]["value"]
            iv_rv_ratio = iv_spx / rv20 if rv20 > 0 else 1.0
            if iv_rv_ratio > 1.2:
                rv_signal = f"IV > RV ✅ (יחס: {iv_rv_ratio:.2f})"
                rv_score  = 80
                rv_note   = "אופציות יקרות ביחס לתנודתיות בפועל — עדיף למכור"
            elif iv_rv_ratio < 0.9:
                rv_signal = f"IV < RV ❌ (יחס: {iv_rv_ratio:.2f})"
                rv_score  = 30
                rv_note   = "אופציות זולות — שקול לקנות במקום למכור"
            else:
                rv_signal = f"IV ≈ RV (יחס: {iv_rv_ratio:.2f})"
                rv_score  = 55
                rv_note   = "מחיר הוגן — מכור בסלקטיביות"
            score += rv_score * 0.15
            signals["rv_iv"] = {
                "signal": rv_signal,
                "note":   rv_note,
                "rv":     round(rv20, 1),
                "score":  rv_score,
            }
        else:
            score += 50 * 0.15
    except Exception:
        score += 50 * 0.15

    # ── 5. Put-Call Ratio (approximate from SPY OI) ───────────────────────
    try:
        spy_tick = yf.Ticker("SPY")
        expiries = spy_tick.options
        if expiries:
            chain   = spy_tick.option_chain(expiries[0])
            put_oi  = int(chain.puts["openInterest"].fillna(0).sum())  if not chain.puts.empty  else 0
            call_oi = int(chain.calls["openInterest"].fillna(0).sum()) if not chain.calls.empty else 0
            pcr     = put_oi / call_oi if call_oi > 0 else 1.0
            if pcr > 1.2:
                pcr_signal = f"פחד (PCR: {pcr:.2f}) 📉"
                pcr_score  = 80
                pcr_note   = "PCR גבוה = פחד קיצוני — טוב למוכרי פוטים"
            elif pcr < 0.7:
                pcr_signal = f"שאננות (PCR: {pcr:.2f}) ⚠️"
                pcr_score  = 40
                pcr_note   = "PCR נמוך = שאננות — זהירות מהצד השורי"
            else:
                pcr_signal = f"נורמלי (PCR: {pcr:.2f})"
                pcr_score  = 65
                pcr_note   = "PCR תקין"
            score += pcr_score * 0.10
            signals["pcr"] = {"signal": pcr_signal, "note": pcr_note, "score": pcr_score}
        else:
            score += 50 * 0.10
    except Exception:
        score += 50 * 0.10

    # ── 6. Cross-reference MongoDB training events ────────────────────────
    try:
        from app.data.mongo_client import MongoDB
        db     = MongoDB.get_db()
        cutoff = datetime.now() - timedelta(days=30)
        events = list(db["training_events"].find({
            "labeled": True,
            "label":   {"$ne": None},
            "scan_at": {"$gte": cutoff},
        }).limit(100))

        if events:
            winners  = sum(1 for e in events if e.get("label") is True)
            win_rate = winners / len(events) * 100

            strat_stats: dict[str, dict] = {}
            for e in events:
                s = e.get("strategy_name") or e.get("strategy") or "unknown"
                if s not in strat_stats:
                    strat_stats[s] = {"wins": 0, "total": 0}
                strat_stats[s]["total"] += 1
                if e.get("label") is True:
                    strat_stats[s]["wins"] += 1

            best_strat = max(
                strat_stats,
                key=lambda s: strat_stats[s]["wins"] / max(strat_stats[s]["total"], 1),
            ) if strat_stats else "iron_condor"

            signals["db_insight"] = {
                "win_rate":      round(win_rate, 1),
                "sample":        len(events),
                "best_strategy": best_strat,
                "note": (
                    f"לפי {len(events)} עסקאות ב-30 הימים האחרונים, "
                    f"אסטרטגיה מנצחת: {best_strat}"
                ),
            }
    except Exception:
        pass

    # ── 7. Final regime verdict ───────────────────────────────────────────
    total_score = min(100.0, max(0.0, score))

    if total_score >= 65:
        regime    = "GREEN"
        regime_he = "🟢 ירוק — מכור פרמיה בביטחון"
        recommendation = (
            "Iron Condor על SPY/QQQ, Bull Put Spread על מניות חזקות.\n"
            "Target delta: 0.15-0.20 | DTE: 30-45 | סגור ב-50% רווח."
        )
    elif total_score >= 40:
        regime    = "YELLOW"
        regime_he = "🟡 צהוב — מכור פרמיה בזהירות"
        recommendation = (
            "Credit Spreads צרים בלבד. הימנע מ-Iron Condor.\n"
            "Target delta: 0.10-0.15 | כנפיים רחבות | גודל חצי."
        )
    else:
        regime    = "RED"
        regime_he = "🔴 אדום — שב בצד!"
        recommendation = (
            "אל תמכור פרמיה! שוק תנודתי מדי.\n"
            "שקול Long Puts/Straddles אם יש מגמה ברורה."
        )

    return {
        "regime":         regime,
        "regime_he":      regime_he,
        "score":          round(total_score, 1),
        "recommendation": recommendation,
        "signals":        signals,
        "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def format_regime_telegram(result: dict) -> str:
    """Format regime analysis as Hebrew Telegram message."""
    s     = result["signals"]
    lines = [
        "📊 *דוח משטר שוק — Citadel Style*",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"🕐 {result['timestamp']}",
        f"\n🏷️ *ציון כולל: {result['score']}/100*",
        result["regime_he"],
        f"\n💡 *המלצה:*\n{result['recommendation']}",
        "\n━━━━━━━━━━━━━━━━━━━━━",
        "📈 *אותות שוק:*",
    ]

    if "vix" in s:
        v = s["vix"]
        lines.append(f"  VIX: `{v['value']}` ({v['regime']}) — {v['note']}")
    if "term_structure" in s:
        ts = s["term_structure"]
        lines.append(f"  עקום: {ts['signal']}")
        if ts["note"]:
            lines.append(f"     {ts['note']}")
    if "trend" in s:
        tr = s["trend"]
        spx_str = f" | SPX: `${tr['spx_price']}`" if tr.get("spx_price") else ""
        lines.append(f"  מגמה: {tr['signal']}{spx_str}")
        if tr["note"]:
            lines.append(f"     {tr['note']}")
    if "rv_iv" in s:
        rv = s["rv_iv"]
        lines.append(f"  RV/IV: {rv['signal']}")
        if rv["note"]:
            lines.append(f"     {rv['note']}")
    if "pcr" in s:
        pc = s["pcr"]
        lines.append(f"  PCR: {pc['signal']}")
        if pc["note"]:
            lines.append(f"     {pc['note']}")
    if "db_insight" in s:
        db = s["db_insight"]
        lines.append(f"\n🤖 *תובנת ML ({db['sample']} עסקאות):*")
        lines.append(f"  {db['note']} | Win rate: `{db['win_rate']}%`")

    return "\n".join(lines)
