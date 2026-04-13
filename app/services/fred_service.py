"""
fred_service.py — FRED Macro Data Service
==========================================

Uses fredapi to pull real Federal Reserve economic data.
Replaces hardcoded/approximated macro values in Agent 1.

Free API key: https://fred.stlouisfed.org/docs/api/api_key.html
Set FRED_API_KEY in environment variables.

Data pulled:
- Federal Funds Rate (DFF)
- CPI YoY inflation (CPIAUCSL)
- 10-Year Treasury Yield (GS10)
- Unemployment Rate (UNRATE)
- VIX (VIXCLS)
- S&P 500 (SP500)
- US Recession Probability (RECPROUSM156N)

Cost: completely free. Rate limit: 120 requests/minute.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MacroSnapshot:
    # Interest rates
    fed_funds_rate: float       # Federal Funds Rate %
    treasury_10y: float         # 10-Year Treasury Yield %
    yield_curve: float          # 10Y - 2Y spread (recession indicator)

    # Inflation
    cpi_yoy: float              # CPI Year-over-Year %
    pce_yoy: float              # PCE inflation (Fed's preferred measure)

    # Labor market
    unemployment_rate: float    # Unemployment Rate %

    # Market
    vix: float                  # VIX fear index
    sp500_level: float          # S&P 500 price level
    sp500_change_1m: float      # S&P 500 1-month change %

    # Regime classification
    regime: str                 # "expansion" | "slowdown" | "recession" | "recovery"
    recession_probability: float # 0-100%

    # Data quality
    data_source: str            # "fred" | "fallback"
    as_of_date: str             # date of most recent data point


def get_macro_snapshot() -> MacroSnapshot:
    """
    Fetch comprehensive macro data from FRED.
    Falls back to safe defaults if API key missing or call fails.
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        logger.warning("FRED_API_KEY not set — using fallback macro data")
        return _fallback_snapshot()

    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
        return _fetch_from_fred(fred)
    except ImportError:
        logger.error("fredapi not installed. Run: pip install fredapi")
        return _fallback_snapshot()
    except Exception as e:
        logger.warning("FRED fetch failed: %s — using fallback", e)
        return _fallback_snapshot()


def _fetch_from_fred(fred) -> MacroSnapshot:
    """Fetch all macro series from FRED."""
    end = datetime.today()
    start_1m = end - timedelta(days=35)
    start_1y = end - timedelta(days=400)

    def latest(series_id: str, start=start_1m) -> float:
        """Get the most recent value for a FRED series."""
        try:
            data = fred.get_series(series_id, observation_start=start)
            data = data.dropna()
            if data.empty:
                return 0.0
            return round(float(data.iloc[-1]), 4)
        except Exception as e:
            logger.debug("FRED series %s failed: %s", series_id, e)
            return 0.0

    # Fetch all series
    fed_rate     = latest("DFF")           # Federal Funds Rate (daily)
    treasury_10y = latest("GS10")          # 10-Year Treasury (monthly)
    treasury_2y  = latest("GS2")           # 2-Year Treasury (monthly)
    yield_curve  = round(treasury_10y - treasury_2y, 4)

    # CPI YoY — calculate from monthly data
    try:
        cpi_data = fred.get_series("CPIAUCSL", observation_start=start_1y)
        cpi_data = cpi_data.dropna()
        if len(cpi_data) >= 13:
            cpi_yoy = round((cpi_data.iloc[-1] / cpi_data.iloc[-13] - 1) * 100, 2)
        else:
            cpi_yoy = 0.0
    except Exception:
        cpi_yoy = 0.0

    # PCE YoY
    try:
        pce_data = fred.get_series("PCEPI", observation_start=start_1y)
        pce_data = pce_data.dropna()
        if len(pce_data) >= 13:
            pce_yoy = round((pce_data.iloc[-1] / pce_data.iloc[-13] - 1) * 100, 2)
        else:
            pce_yoy = 0.0
    except Exception:
        pce_yoy = 0.0

    unemployment = latest("UNRATE", start=start_1m)
    vix          = latest("VIXCLS", start=start_1m)

    # S&P 500
    try:
        sp_data = fred.get_series("SP500", observation_start=start_1m)
        sp_data = sp_data.dropna()
        sp500_level = round(float(sp_data.iloc[-1]), 2) if not sp_data.empty else 0.0
        sp500_1m_ago = round(float(sp_data.iloc[0]), 2) if not sp_data.empty else sp500_level
        sp500_change_1m = round((sp500_level / sp500_1m_ago - 1) * 100, 2) if sp500_1m_ago > 0 else 0.0
    except Exception:
        sp500_level = 0.0
        sp500_change_1m = 0.0

    # Recession probability
    try:
        rec_data = fred.get_series("RECPROUSM156N", observation_start=start_1m)
        rec_data = rec_data.dropna()
        recession_prob = round(float(rec_data.iloc[-1]), 1) if not rec_data.empty else 10.0
    except Exception:
        recession_prob = 10.0

    # Classify regime
    regime = _classify_regime(
        fed_rate=fed_rate,
        cpi_yoy=cpi_yoy,
        unemployment=unemployment,
        yield_curve=yield_curve,
        sp500_change_1m=sp500_change_1m,
        recession_prob=recession_prob,
    )

    as_of = datetime.today().strftime("%Y-%m-%d")

    logger.info(
        "FRED macro: Fed=%.2f%% CPI=%.1f%% PCE=%.1f%% Unemp=%.1f%% "
        "VIX=%.1f Yield_curve=%.2f%% Regime=%s RecProb=%.0f%%",
        fed_rate, cpi_yoy, pce_yoy, unemployment,
        vix, yield_curve, regime, recession_prob,
    )

    return MacroSnapshot(
        fed_funds_rate=fed_rate,
        treasury_10y=treasury_10y,
        yield_curve=yield_curve,
        cpi_yoy=cpi_yoy,
        pce_yoy=pce_yoy,
        unemployment_rate=unemployment,
        vix=vix,
        sp500_level=sp500_level,
        sp500_change_1m=sp500_change_1m,
        regime=regime,
        recession_probability=recession_prob,
        data_source="fred",
        as_of_date=as_of,
    )


def _classify_regime(
    fed_rate: float,
    cpi_yoy: float,
    unemployment: float,
    yield_curve: float,
    sp500_change_1m: float,
    recession_prob: float,
) -> str:
    """
    Classify the current macro regime based on FRED data.
    Used by Agent 1 to set the trading context.
    """
    # Recession signals
    if recession_prob > 50 or yield_curve < -0.5:
        return "recession"

    # Slowdown signals
    if (yield_curve < 0 or sp500_change_1m < -5 or
            (cpi_yoy > 5 and fed_rate > 5)):
        return "slowdown"

    # High inflation / stagflation
    if cpi_yoy > 4 and unemployment > 5:
        return "stagflation"

    # Recovery signals
    if sp500_change_1m > 3 and unemployment < 5 and cpi_yoy < 3.5:
        return "recovery"

    # Default: expansion
    return "expansion"


def _fallback_snapshot() -> MacroSnapshot:
    """Safe defaults when FRED is unavailable."""
    return MacroSnapshot(
        fed_funds_rate=4.33,
        treasury_10y=4.40,
        yield_curve=0.10,
        cpi_yoy=2.8,
        pce_yoy=2.5,
        unemployment_rate=4.1,
        vix=20.0,
        sp500_level=5500.0,
        sp500_change_1m=0.0,
        regime="expansion",
        recession_probability=15.0,
        data_source="fallback",
        as_of_date=datetime.today().strftime("%Y-%m-%d"),
    )


def format_for_telegram(snapshot: MacroSnapshot) -> str:
    """Format macro snapshot for Telegram display in Agent 1 report."""
    regime_emoji = {
        "expansion": "🟢",
        "recovery": "🔵",
        "slowdown": "🟡",
        "stagflation": "🟠",
        "recession": "🔴",
    }.get(snapshot.regime, "⚪")

    yield_curve_str = (
        f"`{snapshot.yield_curve:+.2f}%` ⚠️ inverted"
        if snapshot.yield_curve < 0
        else f"`{snapshot.yield_curve:+.2f}%` ✅"
    )

    return (
        f"🌍 *מאקרו — FRED Data ({snapshot.as_of_date}):*\n"
        f"• Fed Rate: `{snapshot.fed_funds_rate:.2f}%`\n"
        f"• 10Y Treasury: `{snapshot.treasury_10y:.2f}%`\n"
        f"• Yield Curve (10Y-2Y): {yield_curve_str}\n"
        f"• CPI YoY: `{snapshot.cpi_yoy:.1f}%`\n"
        f"• PCE YoY: `{snapshot.pce_yoy:.1f}%` _(Fed target: 2%)_\n"
        f"• Unemployment: `{snapshot.unemployment_rate:.1f}%`\n"
        f"• Recession Probability: `{snapshot.recession_probability:.0f}%`\n"
        f"• S&P 500: `{snapshot.sp500_level:,.0f}` "
        f"({snapshot.sp500_change_1m:+.1f}% החודש)\n"
        f"• {regime_emoji} Regime: *{snapshot.regime.upper()}*\n"
        f"• Source: `{snapshot.data_source}`"
    )
