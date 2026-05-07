"""
barchart_gex.py — Real-Time GEX from Barchart.com
===================================================

Barchart publishes live GEX data for SPX, SPY, QQQ for free.
Updates every ~15 minutes during market hours.

What we get:
- GEX by Strike (positive/negative)
- Call Resistance level
- Put Support level
- HVL (High Volatility Level = Gamma Flip)
- Net GEX total
- Spot price

Source: barchart.com/stocks/quotes/$SPX/gamma-exposure
No API key needed.
"""

import logging
import time
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_cache: dict = {}
_GEX_TTL = 900  # 15 minutes


@dataclass
class BarchartGEX:
    symbol: str
    spot_price: float
    timestamp: str

    # Key levels (the most important)
    call_resistance: float    # Call Wall — תקרת ההתנגדות
    put_support: float        # Put Wall — רצפת התמיכה
    hvl: float                # High Volatility Level = Gamma Flip
    net_gex: float            # Total net GEX ($B)

    # Regime
    gamma_regime: str         # "POSITIVE" | "NEGATIVE"

    # Strike-level data (top 10 strikes)
    strikes: list
    gex_values: list          # Positive = green, Negative = red

    # Bounce vs Breakdown signal
    put_wall_signal: str      # "BOUNCE_LIKELY" | "BREAKDOWN_RISK" | "NEUTRAL"
    put_wall_note: str        # Hebrew explanation


def _fetch_barchart_page(symbol: str) -> Optional[str]:
    """Fetch Barchart GEX page."""
    symbol_map = {
        "SPX": "$SPX",
        "SPY": "SPY",
        "QQQ": "QQQ",
        "NDX": "$NDX",
    }
    bc_symbol = symbol_map.get(symbol.upper(), symbol)
    url = f"https://www.barchart.com/stocks/quotes/{bc_symbol}/gamma-exposure"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.barchart.com/",
    }

    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except ImportError:
        pass

    try:
        import requests
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        logger.debug("Barchart fetch failed: %s", e)

    return None


def _parse_barchart_gex(html: str, symbol: str) -> Optional[BarchartGEX]:
    """Parse GEX data from Barchart HTML."""
    from bs4 import BeautifulSoup
    import json

    try:
        soup = BeautifulSoup(html, "html.parser")

        call_resistance = 0.0
        put_support = 0.0
        hvl = 0.0
        spot_price = 0.0
        net_gex = 0.0
        strikes = []
        gex_values = []

        # Method 1: Look for JSON data in script tags
        for script in soup.find_all("script"):
            text = script.string or ""
            if not text:
                continue

            if "callResistance" in text or "Call Resistance" in text:
                matches = re.findall(
                    r'(?:callResistance|Call Resistance)["\s:]+([0-9,]+\.?[0-9]*)',
                    text
                )
                if matches:
                    call_resistance = float(matches[0].replace(",", ""))

            if "putSupport" in text or "Put Support" in text:
                matches = re.findall(
                    r'(?:putSupport|Put Support)["\s:]+([0-9,]+\.?[0-9]*)',
                    text
                )
                if matches:
                    put_support = float(matches[0].replace(",", ""))

            if "hvl" in text.lower() or "HVL" in text:
                matches = re.findall(
                    r'(?:hvl|HVL)["\s:]+([0-9,]+\.?[0-9]*)',
                    text, re.IGNORECASE
                )
                if matches:
                    hvl = float(matches[0].replace(",", ""))

            if "gamma" in text.lower() and "[" in text:
                try:
                    json_matches = re.findall(
                        r'\{[^{}]*"strike"[^{}]*"gamma"[^{}]*\}',
                        text
                    )
                    for jm in json_matches[:20]:
                        try:
                            obj = json.loads(jm)
                            strike = float(obj.get("strike", 0))
                            gamma = float(obj.get("gamma", obj.get("gex", 0)))
                            if strike > 0:
                                strikes.append(strike)
                                gex_values.append(gamma / 1e9)
                        except Exception:
                            continue
                except Exception:
                    pass

        # Method 2: Parse HTML table
        if not strikes:
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        try:
                            strike_text = cells[0].get_text(strip=True).replace(",", "")
                            gex_text = cells[1].get_text(strip=True).replace(",", "").replace("$", "")
                            if re.match(r'^\d+\.?\d*$', strike_text):
                                strike = float(strike_text)
                                gex = float(gex_text) if gex_text else 0
                                if 100 < strike < 100000:
                                    strikes.append(strike)
                                    gex_values.append(gex / 1e9)
                        except Exception:
                            continue

        # Method 3: Parse page text
        page_text = soup.get_text()

        price_matches = re.findall(r'(?:Last|Price|Spot)[:\s]+\$?([0-9,]+\.?[0-9]*)', page_text)
        for pm in price_matches:
            val = float(pm.replace(",", ""))
            if 1 < val < 100000:
                spot_price = val
                break

        if call_resistance == 0:
            cr_matches = re.findall(
                r'Call\s+Resistance[:\s]+\$?([0-9,]+\.?[0-9]*)',
                page_text
            )
            if cr_matches:
                call_resistance = float(cr_matches[0].replace(",", ""))

        if put_support == 0:
            ps_matches = re.findall(
                r'Put\s+Support[:\s]+\$?([0-9,]+\.?[0-9]*)',
                page_text
            )
            if ps_matches:
                put_support = float(ps_matches[0].replace(",", ""))

        if hvl == 0:
            hvl_matches = re.findall(
                r'HVL[:\s]+\$?([0-9,]+\.?[0-9]*)',
                page_text
            )
            if hvl_matches:
                hvl = float(hvl_matches[0].replace(",", ""))

        if not call_resistance or not put_support:
            logger.info("Barchart parse incomplete — using yfinance GEX fallback")
            return _yfinance_gex_fallback(symbol)

        net_gex = sum(gex_values) if gex_values else 0
        gamma_regime = "POSITIVE" if spot_price > hvl else "NEGATIVE"

        put_wall_signal, put_wall_note = _analyze_put_wall(
            symbol, spot_price, put_support, gex_values, strikes
        )

        return BarchartGEX(
            symbol=symbol,
            spot_price=spot_price,
            timestamp=datetime.now().strftime("%d/%m %H:%M"),
            call_resistance=call_resistance,
            put_support=put_support,
            hvl=hvl,
            net_gex=round(net_gex, 2),
            gamma_regime=gamma_regime,
            strikes=strikes[:20],
            gex_values=gex_values[:20],
            put_wall_signal=put_wall_signal,
            put_wall_note=put_wall_note,
        )

    except Exception as e:
        logger.error("Barchart parse failed: %s", e)
        return _yfinance_gex_fallback(symbol)


def _analyze_put_wall(
    symbol: str,
    spot: float,
    put_support: float,
    gex_values: list,
    strikes: list,
) -> tuple:
    """
    Analyze whether Put Wall will Bounce or Breakdown.

    Key insight:
    - If spot is near Put Support AND new put demand is emerging → BREAKDOWN_RISK
    - If spot is near Put Support AND put demand is fading → BOUNCE_LIKELY
    """
    if not put_support or not spot:
        return "NEUTRAL", "אין מספיק נתונים לניתוח"

    dist_to_put = (spot / put_support - 1) * 100

    if dist_to_put > 5:
        return "NEUTRAL", f"המחיר רחוק {dist_to_put:.1f}% מ-Put Support — לא רלוונטי כרגע"

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol if symbol != "SPX" else "^GSPC")
        exps = ticker.options

        if not exps:
            return "NEUTRAL", "לא ניתן לבדוק OI"

        chain = ticker.option_chain(exps[0])
        puts = chain.puts

        puts_below = puts[puts["strike"] < put_support]
        if not puts_below.empty:
            new_put_volume = int(puts_below["volume"].fillna(0).sum())
            avg_oi = int(puts_below["openInterest"].fillna(0).mean())

            if new_put_volume > avg_oi * 0.5:
                return (
                    "BREAKDOWN_RISK",
                    f"⚠️ נפח Puts מתחת ל-${put_support:.0f} גבוה ({new_put_volume:,}).\n"
                    f"יש ביקוש חדש לפוטים — סיכון לשבירה ומפל ירידות!\n"
                    f"Dealers נאלצים למכור עוד כשהמחיר יורד."
                )
            else:
                return (
                    "BOUNCE_LIKELY",
                    f"✅ נפח Puts נמוך מתחת לתמיכה — מחזיקים ממשים רווח.\n"
                    f"Dealers יסגרו שורטים → קנייה אגרסיבית → קפיצה צפויה מ-${put_support:.0f}"
                )

    except Exception:
        pass

    if dist_to_put < 1:
        return (
            "BOUNCE_LIKELY",
            f"המחיר נוגע ב-Put Support (${put_support:.0f}).\n"
            f"בדרך כלל נקבל קפיצה אם אין ביקוש חדש לפוטים."
        )

    return "NEUTRAL", f"המחיר מתקרב לתמיכה ({dist_to_put:.1f}% מרחק)"


def _yfinance_gex_fallback(symbol: str) -> Optional[BarchartGEX]:
    """Fallback to our own yfinance GEX calculation."""
    try:
        from app.services.gex_calculator import calculate_gex

        yf_symbol = {
            "SPX": "SPY", "SPY": "SPY", "QQQ": "QQQ"
        }.get(symbol, symbol)

        g = calculate_gex(yf_symbol)
        if not g:
            return None

        return BarchartGEX(
            symbol=symbol,
            spot_price=g.spot_price,
            timestamp=g.calculation_time,
            call_resistance=g.call_wall,
            put_support=g.put_wall,
            hvl=g.zero_gamma,
            net_gex=g.net_gex,
            gamma_regime=g.gamma_regime,
            strikes=g.strikes[:20],
            gex_values=g.gex_profile[:20],
            put_wall_signal="NEUTRAL",
            put_wall_note="נתונים מחושבים מ-yfinance (לא Barchart)",
        )
    except Exception as e:
        logger.debug("yfinance GEX fallback failed: %s", e)
        return None


def get_realtime_gex(symbol: str = "SPY") -> Optional[BarchartGEX]:
    """
    Get real-time GEX data.
    Tries Barchart first, falls back to yfinance calculation.
    Cached for 15 minutes.
    """
    cache_key = f"gex_{symbol}"
    cached = _cache.get(cache_key)
    if cached:
        data, ts = cached
        if time.time() - ts < _GEX_TTL:
            logger.debug("GEX cache hit for %s", symbol)
            return data

    logger.info("Fetching real-time GEX for %s from Barchart", symbol)

    html = _fetch_barchart_page(symbol)
    if html:
        result = _parse_barchart_gex(html, symbol)
    else:
        logger.info("Barchart fetch failed — using yfinance fallback")
        result = _yfinance_gex_fallback(symbol)

    if result:
        _cache[cache_key] = (result, time.time())
        logger.info(
            "GEX %s: spot=%.0f CR=%.0f PS=%.0f HVL=%.0f regime=%s",
            symbol, result.spot_price, result.call_resistance,
            result.put_support, result.hvl, result.gamma_regime
        )

    return result


def format_gex_realtime_hebrew(g: BarchartGEX) -> str:
    """Format real-time GEX for Telegram."""
    regime_emoji = "🟢" if g.gamma_regime == "POSITIVE" else "🔴"
    net_sign = "+" if g.net_gex >= 0 else ""

    dist_cr = dist_ps = dist_hvl = 0.0
    if g.spot_price > 0:
        if g.call_resistance > 0:
            dist_cr = (g.call_resistance / g.spot_price - 1) * 100
        if g.put_support > 0:
            dist_ps = (g.put_support / g.spot_price - 1) * 100
        if g.hvl > 0:
            dist_hvl = (g.hvl / g.spot_price - 1) * 100

    signal_emoji = {
        "BOUNCE_LIKELY": "🟢",
        "BREAKDOWN_RISK": "🔴",
        "NEUTRAL": "⚪",
    }.get(g.put_wall_signal, "⚪")

    strategy_line = (
        f"מעל ${g.hvl:,.0f} — שוק יציב, Dealers מייצבים\n"
        f"מכור פרמיה: Iron Condor בין ${g.put_support:,.0f}–${g.call_resistance:,.0f}"
        if g.gamma_regime == "POSITIVE"
        else
        f"מתחת ל-${g.hvl:,.0f} — שוק תנודתי, Dealers מאיצים\n"
        f"זהירות ממכירת פרמיה! שקול Long Options"
    )

    return (
        f"📊 GEX בזמן אמת — {g.symbol}\n"
        f"──────────────────────────\n"
        f"💵 מחיר: ${g.spot_price:,.0f} | {g.timestamp}\n\n"
        f"{regime_emoji} Gamma Regime: {g.gamma_regime}\n\n"
        f"רמות מפתח:\n"
        f"🔴 Call Resistance (תקרה): ${g.call_resistance:,.0f} ({dist_cr:+.1f}%)\n"
        f"⚡ HVL / Gamma Flip: ${g.hvl:,.0f} ({dist_hvl:+.1f}%)\n"
        f"🟢 Put Support (תמיכה): ${g.put_support:,.0f} ({dist_ps:+.1f}%)\n"
        f"💰 Net GEX: ${net_sign}{g.net_gex:.1f}B\n\n"
        f"──────────────────────────\n"
        f"{signal_emoji} ניתוח Put Wall:\n"
        f"{g.put_wall_note}\n\n"
        f"──────────────────────────\n"
        f"מה המשמעות:\n"
        f"{strategy_line}"
    )


def get_gex_for_zerod(symbol: str = "SPY") -> dict:
    """
    Get GEX levels specifically for 0DTE trading.
    Returns the most critical levels for intraday decisions.
    """
    g = get_realtime_gex(symbol)
    if not g:
        return {}

    return {
        "call_resistance": g.call_resistance,
        "put_support": g.put_support,
        "hvl": g.hvl,
        "gamma_regime": g.gamma_regime,
        "spot": g.spot_price,
        "max_safe_call_strike": g.call_resistance - 1,
        "min_safe_put_strike": g.put_support + 1,
        "put_wall_signal": g.put_wall_signal,
        "intraday_range": f"${g.put_support:,.0f}–${g.call_resistance:,.0f}",
    }
