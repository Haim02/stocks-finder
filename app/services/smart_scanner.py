"""
smart_scanner.py — Deep Intelligence Stock Scanner
===================================================

Goes beyond technical indicators to find:
1. MOMENTUM stocks — strong price + volume + earnings acceleration
2. FUNDAMENTAL strength — revenue growth, margins, AI/tech investment
3. INSTITUTIONAL money — unusual options volume, volume anomalies
4. TREND/REVOLUTION plays — AI, biotech, clean energy, defense, space
5. CATALYST-driven — FDA, M&A, product launch, analyst upgrades
6. SECTOR ROTATION — what sectors are hot this week/month

The difference:
❌ "AMZN RSI=93, IV Rank=-9%, כרגע לא אידאלי"
✅ "AMZN עלתה 49%: AWS AI revenue +25% YoY, $4B השקעה ב-Anthropic,
    operating margin הוכפל → Bull Call Spread לחודשיים"
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

TREND_THEMES = {
    "AI_INFRASTRUCTURE": ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "PLTR", "SMCI"],
    "AI_APPLICATIONS":   ["AAPL", "CRM", "NOW", "SNOW", "DDOG", "BBAI"],
    "DEFENSE_SECURITY":  ["LMT", "RTX", "NOC", "GD", "CACI", "LDOS", "AXON"],
    "CLEAN_ENERGY":      ["ENPH", "FSLR", "NEE", "PLUG", "BE", "SEDG"],
    "BIOTECH_PHARMA":    ["LLY", "NVO", "MRNA", "REGN", "VRTX", "GILD"],
    "FINTECH":           ["V", "MA", "SQ", "PYPL", "COIN", "HOOD"],
    "SPACE_TECH":        ["RKLB", "BA", "LMT"],
    "CONSUMER_MOMENTUM": ["AMZN", "TSLA", "NFLX", "UBER", "ABNB"],
}


@dataclass
class SmartScanResult:
    ticker: str
    company_name: str
    sector: str
    price: float
    price_change_1w: float
    price_change_1m: float
    price_change_3m: float
    at_52w_high: bool
    pct_from_52w_low: float
    revenue_growth_yoy: Optional[float]
    earnings_growth_yoy: Optional[float]
    profit_margin: Optional[float]
    pe_ratio: Optional[float]
    market_cap_b: float
    rsi_14: float
    volume_ratio: float
    price_above_ma50: bool
    price_above_ma200: bool
    trend_strength: str         # "STRONG_UP" | "UP" | "NEUTRAL" | "DOWN"
    has_earnings_catalyst: bool
    earnings_days: Optional[int]
    analyst_rating: str
    analyst_target: Optional[float]
    upside_to_target: Optional[float]
    trend_themes: list[str]
    institutional_signal: str   # "ACCUMULATING" | "DISTRIBUTING" | "NEUTRAL"
    unusual_options: bool
    recent_catalyst: str
    perplexity_insight: str
    momentum_score: float
    fundamental_score: float
    opportunity_score: float
    recommended_strategy: str
    strategy_reason: str


def _get_fundamental_data(ticker: str) -> dict:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return {
            "name": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", "Unknown"),
            "market_cap": (info.get("marketCap") or 0) / 1e9,
            "pe": info.get("trailingPE"),
            "revenue_growth": (info.get("revenueGrowth") or 0) * 100,
            "earnings_growth": (info.get("earningsGrowth") or 0) * 100,
            "profit_margin": (info.get("profitMargins") or 0) * 100,
            "analyst_target": info.get("targetMeanPrice"),
            "analyst_rating": (info.get("recommendationKey") or "hold").upper(),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "short_pct": (info.get("shortPercentOfFloat") or 0) * 100,
            "beta": info.get("beta", 1.0),
        }
    except Exception as e:
        logger.debug("Fundamental data failed for %s: %s", ticker, e)
        return {}


def _get_momentum_data(ticker: str) -> dict:
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty or len(hist) < 20:
            return {}

        closes = hist["Close"]
        volumes = hist["Volume"]
        price = float(closes.iloc[-1])

        def safe_pct(days: int) -> float:
            return round(float((price / closes.iloc[-days] - 1) * 100), 1) if len(closes) > days else 0.0

        ma50 = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else price
        ma200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else price

        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = float(100 - (100 / (1 + gain / loss)).iloc[-1])

        avg_vol = float(volumes.rolling(30).mean().iloc[-1])
        vol_ratio = round(float(volumes.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0, 2)

        high_52w = float(closes.rolling(252).max().iloc[-1]) if len(closes) >= 252 else float(closes.max())
        low_52w = float(closes.rolling(252).min().iloc[-1]) if len(closes) >= 252 else float(closes.min())

        chg_1m = safe_pct(21)
        if price > ma50 > ma200 and chg_1m > 10:
            trend = "STRONG_UP"
        elif price > ma50 and chg_1m > 0:
            trend = "UP"
        elif price < ma50 < ma200:
            trend = "DOWN"
        else:
            trend = "NEUTRAL"

        return {
            "price": round(price, 2),
            "chg_1w": safe_pct(5),
            "chg_1m": chg_1m,
            "chg_3m": safe_pct(63),
            "rsi": round(rsi, 1),
            "vol_ratio": vol_ratio,
            "above_ma50": price > ma50,
            "above_ma200": price > ma200,
            "trend": trend,
            "at_52w_high": price >= high_52w * 0.97,
            "pct_from_52w_low": round((price - low_52w) / low_52w * 100, 1) if low_52w > 0 else 0.0,
        }
    except Exception as e:
        logger.debug("Momentum data failed for %s: %s", ticker, e)
        return {}


def _get_perplexity_insight(ticker: str, company_name: str, recent_move: float) -> str:
    """
    Ask Perplexity WHY the stock is moving — the key differentiator from pure technicals.
    """
    try:
        from app.services.perplexity_service import PerplexityService
        svc = PerplexityService()
        if not svc.is_available():
            return ""
        direction = "rising" if recent_move > 0 else "falling"
        query = (
            f"Why is {company_name} ({ticker}) stock {direction} ({recent_move:+.0f}% recently)? "
            f"Today is {date.today().strftime('%B %d, %Y')}. Include: "
            f"1) Main catalyst (earnings, AI investment, product, M&A, regulation) "
            f"2) Revenue/earnings trend "
            f"3) Major institutional investment or partnership? "
            f"4) Bull vs bear case. "
            f"Answer in 3-4 sentences in Hebrew."
        )
        answer = svc.ask(query)
        return answer[:300] if answer else ""
    except Exception:
        return ""


def _detect_trend_themes(ticker: str) -> list[str]:
    return [theme for theme, tickers in TREND_THEMES.items() if ticker.upper() in tickers]


def _score_opportunity(
    fund: dict, mom: dict, has_earnings: bool,
    analyst_rating: str, upside: Optional[float],
) -> tuple[float, float, float]:
    m_score = 50.0
    chg_1m = mom.get("chg_1m", 0)
    if chg_1m > 20:
        m_score += 25
    elif chg_1m > 10:
        m_score += 15
    elif chg_1m > 5:
        m_score += 10
    elif chg_1m < -10:
        m_score -= 20
    if mom.get("trend") == "STRONG_UP":
        m_score += 15
    elif mom.get("trend") == "UP":
        m_score += 8
    vol_ratio = mom.get("vol_ratio", 1.0)
    if vol_ratio > 2.0:
        m_score += 10
    elif vol_ratio > 1.5:
        m_score += 5
    if mom.get("at_52w_high"):
        m_score += 10
    m_score = max(0.0, min(100.0, m_score))

    f_score = 50.0
    rev_growth = fund.get("revenue_growth", 0)
    if rev_growth > 30:
        f_score += 20
    elif rev_growth > 15:
        f_score += 12
    elif rev_growth > 5:
        f_score += 6
    elif rev_growth < 0:
        f_score -= 15
    margin = fund.get("profit_margin", 0)
    if margin > 25:
        f_score += 15
    elif margin > 15:
        f_score += 8
    elif margin < 0:
        f_score -= 15
    if analyst_rating in ("STRONG_BUY", "STRONGBUY"):
        f_score += 15
    elif analyst_rating == "BUY":
        f_score += 8
    if upside and upside > 20:
        f_score += 10
    elif upside and upside > 10:
        f_score += 5
    f_score = max(0.0, min(100.0, f_score))

    opp = m_score * 0.55 + f_score * 0.45
    if has_earnings:
        opp -= 10
    opp = max(0.0, min(100.0, opp))
    return round(m_score, 1), round(f_score, 1), round(opp, 1)


def _recommend_strategy(
    ticker: str, price: float, iv_rank: float, trend: str, rsi: float,
    upside: Optional[float], has_earnings: bool, earnings_days: Optional[int],
    momentum_score: float,
) -> tuple[str, str]:
    if has_earnings and earnings_days and 3 <= earnings_days <= 14:
        if iv_rank < 30:
            return (
                "Long Straddle לפני Earnings",
                f"Earnings בעוד {earnings_days} ימים + IV נמוך → קנה תנודתיות בזול לפני הדוח",
            )
        return (
            "Iron Condor לפני Earnings (זהירות)",
            f"Earnings בעוד {earnings_days} ימים + IV גבוה → מכור Strangle רחב, צא לפני הדוח",
        )
    if trend == "STRONG_UP" and momentum_score >= 75:
        if iv_rank >= 50:
            return (
                "Bull Call Spread (Debit)",
                "מומנטום חזק + IV גבוה → Bull Call Spread — הגדר סיכון ותשתתף בעלייה",
            )
        return (
            "Long Call LEAPs (6-12 חודש)",
            "מומנטום חזק + IV נמוך → קנה LEAPs זולים לניצול המגמה לטווח ארוך",
        )
    if iv_rank >= 50:
        if trend in ("UP", "STRONG_UP"):
            return "Bull Put Spread (Credit)", f"IV Rank {iv_rank:.0f}% גבוה + מגמה שורית → מכור Bull Put Spread"
        elif trend == "DOWN":
            return "Bear Call Spread (Credit)", f"IV Rank {iv_rank:.0f}% גבוה + מגמה דובית → מכור Bear Call Spread"
        return "Iron Condor", f"IV Rank {iv_rank:.0f}% גבוה + ניטרלי → Iron Condor"
    if upside and upside > 25 and trend in ("UP", "STRONG_UP"):
        return "Covered Call / PMCC", f"יעד אנליסטים {upside:.0f}% מעל המחיר → PMCC: קנה LEAPs מכור Calls"
    if iv_rank < 25:
        return "Long Call LEAPs", f"IV Rank {iv_rank:.0f}% נמוך → אופציות זולות → קנה Calls לטווח ארוך"
    return "המתן להזדמנות טובה יותר", f"אין תנאי אידאלי כרגע — עקוב אחרי המניה"


def deep_scan_ticker(ticker: str, fetch_perplexity: bool = True) -> Optional[SmartScanResult]:
    """
    Full deep scan: fundamentals + momentum + AI insight + IV + earnings.
    """
    import yfinance as yf

    fund = _get_fundamental_data(ticker)
    mom = _get_momentum_data(ticker)
    if not fund or not mom:
        return None

    price = mom.get("price", 0)
    if price <= 0:
        return None

    iv_rank = 30.0
    try:
        from app.services.realtime_market_data import get_realtime_iv_data
        iv_rank = get_realtime_iv_data(ticker).iv_rank
    except Exception:
        pass

    has_earnings, earnings_days = False, None
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is not None and not cal.empty and "Earnings Date" in cal.index:
            earn = cal.loc["Earnings Date"]
            if hasattr(earn, "iloc"):
                earn = earn.iloc[0]
            if hasattr(earn, "date"):
                earn = earn.date()
            days = (earn - date.today()).days
            if -2 <= days <= 60:
                has_earnings, earnings_days = True, days
    except Exception:
        pass

    analyst_rating = fund.get("analyst_rating", "HOLD")
    analyst_target = fund.get("analyst_target")
    upside = round((analyst_target / price - 1) * 100, 1) if analyst_target and price > 0 else None

    m_score, f_score, opp_score = _score_opportunity(fund, mom, has_earnings, analyst_rating, upside)

    insight = ""
    if fetch_perplexity and mom.get("chg_1m", 0) != 0:
        insight = _get_perplexity_insight(ticker, fund.get("name", ticker), mom.get("chg_1m", 0))

    vol_ratio = mom.get("vol_ratio", 1.0)
    chg_1m = mom.get("chg_1m", 0)
    if vol_ratio > 1.8 and chg_1m > 5:
        inst_signal = "ACCUMULATING"
    elif vol_ratio > 1.8 and chg_1m < -5:
        inst_signal = "DISTRIBUTING"
    else:
        inst_signal = "NEUTRAL"

    strategy, strategy_reason = _recommend_strategy(
        ticker, price, iv_rank, mom.get("trend", "NEUTRAL"),
        mom.get("rsi", 50), upside, has_earnings, earnings_days, m_score,
    )

    return SmartScanResult(
        ticker=ticker,
        company_name=fund.get("name", ticker),
        sector=fund.get("sector", "Unknown"),
        price=price,
        price_change_1w=mom.get("chg_1w", 0),
        price_change_1m=chg_1m,
        price_change_3m=mom.get("chg_3m", 0),
        at_52w_high=mom.get("at_52w_high", False),
        pct_from_52w_low=mom.get("pct_from_52w_low", 0),
        revenue_growth_yoy=fund.get("revenue_growth"),
        earnings_growth_yoy=fund.get("earnings_growth"),
        profit_margin=fund.get("profit_margin"),
        pe_ratio=fund.get("pe"),
        market_cap_b=round(fund.get("market_cap", 0), 1),
        rsi_14=mom.get("rsi", 50),
        volume_ratio=vol_ratio,
        price_above_ma50=mom.get("above_ma50", False),
        price_above_ma200=mom.get("above_ma200", False),
        trend_strength=mom.get("trend", "NEUTRAL"),
        has_earnings_catalyst=has_earnings,
        earnings_days=earnings_days,
        analyst_rating=analyst_rating,
        analyst_target=analyst_target,
        upside_to_target=upside,
        trend_themes=_detect_trend_themes(ticker),
        institutional_signal=inst_signal,
        unusual_options=vol_ratio > 2.5,
        recent_catalyst=insight[:150] if insight else "",
        perplexity_insight=insight,
        momentum_score=m_score,
        fundamental_score=f_score,
        opportunity_score=opp_score,
        recommended_strategy=strategy,
        strategy_reason=strategy_reason,
    )


def format_smart_scan_hebrew(r: SmartScanResult) -> str:

    # Trend emojis
    trend_text = {
        "STRONG_UP": "🚀 עלייה חזקה — המניה במגמה שורית עם מומנטום גבוה",
        "UP": "📈 עלייה — המניה נסחרת מעל הממוצעים הנעים",
        "NEUTRAL": "➡️ ניטרלי — אין כיוון ברור כרגע",
        "DOWN": "📉 ירידה — המניה בלחץ מוכרים",
    }.get(r.trend_strength, "➡️ ניטרלי")

    inst_text = {
        "ACCUMULATING": "🏦 מוסדיים צוברים — Volume גבוה עם עלייה = כסף גדול נכנס",
        "DISTRIBUTING": "⚠️ מוסדיים מוכרים — Volume גבוה עם ירידה = כסף גדול יוצא",
        "NEUTRAL": "⚪ פעילות מוסדית רגילה",
    }.get(r.institutional_signal, "⚪ ניטרלי")

    # RSI explanation
    if r.rsi_14 > 75:
        rsi_text = f"`{r.rsi_14:.0f}` 🔥 קנייה מופרזת — המניה חמה מאוד, זהירות מתיקון"
    elif r.rsi_14 > 60:
        rsi_text = f"`{r.rsi_14:.0f}` ✅ חיובי — מומנטום טוב, לא overbought"
    elif r.rsi_14 > 40:
        rsi_text = f"`{r.rsi_14:.0f}` ➡️ ניטרלי"
    else:
        rsi_text = f"`{r.rsi_14:.0f}` 🧊 מכירה מופרזת — המניה חלשה, שים לב"

    # Volume explanation
    if r.volume_ratio > 2.5:
        vol_text = f"`{r.volume_ratio:.1f}x` 🚨 Volume חריג ביותר — אירוע משמעותי קורה"
    elif r.volume_ratio > 1.8:
        vol_text = f"`{r.volume_ratio:.1f}x` ⚡ Volume גבוה — תנועה אמינה, לא ספקולציה"
    elif r.volume_ratio > 1.2:
        vol_text = f"`{r.volume_ratio:.1f}x` 📊 Volume מעל ממוצע — סיגנל בינוני"
    else:
        vol_text = f"`{r.volume_ratio:.1f}x` Volume רגיל"

    # MA explanation
    if r.price_above_ma50 and r.price_above_ma200:
        ma_text = "✅ מעל MA50 וMA200 — מגמה שורית מאושרת בשני הטווחים"
    elif r.price_above_ma50:
        ma_text = "🟡 מעל MA50 אך מתחת MA200 — שורי לטווח קצר, ניטרלי לטווח ארוך"
    else:
        ma_text = "🔴 מתחת לממוצעים הנעים — מגמה דובית"

    # 52W position
    if r.at_52w_high:
        range_text = "🏔️ שיא שנתי חדש! — עוצמה יוצאת דופן, פריצה לשטח חדש"
    elif r.pct_from_52w_low > 80:
        range_text = f"📈 {r.pct_from_52w_low:.0f}% מעל השפל השנתי — קרוב לשיא"
    elif r.pct_from_52w_low > 50:
        range_text = f"➡️ {r.pct_from_52w_low:.0f}% מעל השפל השנתי — אמצע הטווח"
    else:
        range_text = f"⚠️ {r.pct_from_52w_low:.0f}% מעל השפל השנתי — קרוב לשפל"

    # Fundamental lines with explanations
    fund_lines = []
    if r.revenue_growth_yoy is not None and r.revenue_growth_yoy != 0:
        if r.revenue_growth_yoy > 25:
            fund_lines.append(f"  📈 *צמיחת הכנסות:* `{r.revenue_growth_yoy:+.0f}%` — צמיחה מרשימה מאוד, החברה מתרחבת בקצב גבוה")
        elif r.revenue_growth_yoy > 10:
            fund_lines.append(f"  📈 *צמיחת הכנסות:* `{r.revenue_growth_yoy:+.0f}%` — צמיחה בריאה, עסק גדל")
        elif r.revenue_growth_yoy > 0:
            fund_lines.append(f"  ➡️ *צמיחת הכנסות:* `{r.revenue_growth_yoy:+.0f}%` — צמיחה מתונה")
        else:
            fund_lines.append(f"  📉 *צמיחת הכנסות:* `{r.revenue_growth_yoy:+.0f}%` — ירידה בהכנסות, בעיה פונדמנטלית")

    if r.profit_margin is not None and r.profit_margin != 0:
        if r.profit_margin > 25:
            fund_lines.append(f"  💚 *שולי רווח:* `{r.profit_margin:.0f}%` — רווחיות גבוהה מאוד, עסק יעיל")
        elif r.profit_margin > 10:
            fund_lines.append(f"  🟡 *שולי רווח:* `{r.profit_margin:.0f}%` — רווחיות סבירה")
        elif r.profit_margin > 0:
            fund_lines.append(f"  🟠 *שולי רווח:* `{r.profit_margin:.0f}%` — רווחיות נמוכה, עוקב")
        else:
            fund_lines.append(f"  🔴 *שולי רווח:* `{r.profit_margin:.0f}%` — הפסדי כרגע")

    if r.pe_ratio and r.pe_ratio > 0:
        if r.pe_ratio > 50:
            fund_lines.append(f"  📊 *מכפיל רווח (P/E):* `{r.pe_ratio:.0f}x` — יקר, השוק מתמחר צמיחה עתידית גבוהה")
        elif r.pe_ratio > 25:
            fund_lines.append(f"  📊 *מכפיל רווח (P/E):* `{r.pe_ratio:.0f}x` — ממוצע לחברות צמיחה")
        else:
            fund_lines.append(f"  📊 *מכפיל רווח (P/E):* `{r.pe_ratio:.0f}x` — זול יחסית לסקטור")

    if r.upside_to_target and r.analyst_target:
        if r.upside_to_target > 20:
            fund_lines.append(f"  🎯 *יעד אנליסטים:* `${r.analyst_target:.0f}` — פוטנציאל עלייה של `{r.upside_to_target:.0f}%` לפי וול סטריט")
        elif r.upside_to_target > 0:
            fund_lines.append(f"  🎯 *יעד אנליסטים:* `${r.analyst_target:.0f}` — עוד `{r.upside_to_target:.0f}%` לפי הקונסנזוס")
        else:
            fund_lines.append(f"  ⚠️ *יעד אנליסטים:* `${r.analyst_target:.0f}` — מחיר נוכחי מעל יעד האנליסטים")

    analyst_map = {
        "STRONGBUY": "📢 קנייה חזקה — קונסנזוס חיובי מאוד",
        "STRONG_BUY": "📢 קנייה חזקה",
        "BUY": "👍 קנייה — רוב האנליסטים ממליצים",
        "HOLD": "🤝 החזק — אין המלצה ברורה",
        "SELL": "👎 מכירה",
        "UNDERPERFORM": "📉 ביצוע חסר",
    }
    analyst_str = analyst_map.get(r.analyst_rating, r.analyst_rating)

    # Earnings warning
    earn_str = ""
    if r.has_earnings_catalyst and r.earnings_days is not None:
        if r.earnings_days <= 3:
            earn_str = f"\n🚨 *Earnings בעוד {r.earnings_days} ימים בלבד!*\nזהירות קיצונית — IV יתנפח לפני הדוח וייצנח אחרי"
        elif r.earnings_days <= 7:
            earn_str = f"\n⚠️ *Earnings בעוד {r.earnings_days} ימים* — שקול להמתין לאחרי הדוח"
        elif r.earnings_days <= 14:
            earn_str = f"\n📅 *Earnings בעוד {r.earnings_days} ימים* — אפשר להיכנס, אך עם מודעות"
        else:
            earn_str = f"\n📅 Earnings בעוד {r.earnings_days} ימים — לא בדחיפות"

    # Themes with explanations
    theme_map = {
        "AI_INFRASTRUCTURE": "🤖 תשתית AI — ענן, מעבדים, דאטה סנטרים",
        "AI_APPLICATIONS": "💡 יישומי AI — תוכנה שמשלבת AI במוצרים",
        "DEFENSE_SECURITY": "🛡️ ביטחון — ביקוש גבוה בסביבה גיאופוליטית",
        "CLEAN_ENERGY": "🌱 אנרגיה נקייה — מגמה ארוכת טווח",
        "BIOTECH_PHARMA": "💊 ביוטק/פארמה — תרופות ומחקר",
        "FINTECH": "💳 פינטק — תשלומים ופיננסים דיגיטליים",
        "SPACE_TECH": "🚀 חלל — מגזר צומח",
        "CONSUMER_MOMENTUM": "🛒 צרכנות — מסחר ובידור",
    }
    themes_str = "\n".join(f"  • {theme_map.get(t, t)}" for t in r.trend_themes) if r.trend_themes else ""

    # Score explanation
    if r.opportunity_score >= 80:
        score_verdict = "🟢 הזדמנות מצוינת"
    elif r.opportunity_score >= 65:
        score_verdict = "🟡 הזדמנות טובה"
    elif r.opportunity_score >= 50:
        score_verdict = "🟠 הזדמנות בינונית — שקול בזהירות"
    else:
        score_verdict = "🔴 לא הזמן המתאים"

    score_bar = "█" * int(r.opportunity_score / 10) + "░" * (10 - int(r.opportunity_score / 10))

    insight_str = f"\n💬 *מה קורה עכשיו עם המניה:*\n{r.perplexity_insight}\n" if r.perplexity_insight else ""

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 *{r.ticker} — {r.company_name}*\n"
        f"📍 ענף: {r.sector} | מחיר: `${r.price:.2f}` | שווי: `${r.market_cap_b:.0f}B`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"📊 *ביצועי מחיר:*\n"
        f"  שבוע אחרון: `{r.price_change_1w:+.1f}%`\n"
        f"  חודש אחרון: `{r.price_change_1m:+.1f}%`\n"
        f"  3 חודשים: `{r.price_change_3m:+.1f}%`\n"
        f"  {range_text}\n\n"

        f"📈 *ניתוח מומנטום:*\n"
        f"  {trend_text}\n"
        f"  RSI: {rsi_text}\n"
        f"  עוצמת מסחר: {vol_text}\n"
        f"  {ma_text}\n\n"

        + (f"💼 *ניתוח פונדמנטלי:*\n" + "\n".join(fund_lines) + f"\n  📢 המלצת אנליסטים: {analyst_str}\n\n" if fund_lines else "")

        + (f"🌍 *מגמות עולמיות שהמניה שייכת אליהן:*\n{themes_str}\n\n" if themes_str else "")

        + f"🏦 *פעילות מוסדית:*\n  {inst_text}\n"
        + (f"  🚨 *פעילות אופציות חריגה — כסף גדול מהמר על תנועה*\n" if r.unusual_options else "")

        + earn_str + "\n\n"
        + insight_str

        + f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *אסטרטגיה מומלצת:*\n"
        f"*{r.recommended_strategy}*\n\n"
        f"📝 *הסבר:* {r.strategy_reason}\n\n"

        f"📊 *ציון הזדמנות כולל: {r.opportunity_score:.0f}/100 — {score_verdict}*\n"
        f"`{score_bar}`\n"
        f"מומנטום: `{r.momentum_score:.0f}/100` | פונדמנטלי: `{r.fundamental_score:.0f}/100`"
    )


def scan_trending_themes(top_n: int = 3) -> list[SmartScanResult]:
    """
    Scan which megatrend themes have the hottest momentum right now.
    Returns top_n stocks across all themes, sorted by opportunity_score.
    """
    results = []
    scanned: set[str] = set()

    for theme, tickers in list(TREND_THEMES.items())[:4]:
        for ticker in tickers[:3]:
            if ticker in scanned:
                continue
            scanned.add(ticker)
            try:
                result = deep_scan_ticker(ticker, fetch_perplexity=False)
                if result and result.price_change_1m > 5:
                    results.append(result)
            except Exception:
                continue

    results.sort(key=lambda x: x.opportunity_score, reverse=True)
    return results[:top_n]
