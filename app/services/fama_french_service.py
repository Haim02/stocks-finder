"""
fama_french_service.py — Fama-French Factor Loading for XGBoost
================================================================

Fama-French 3-Factor + Momentum features:
- MKT-RF : Market excess return (market risk premium)
- SMB    : Small Minus Big (small cap vs large cap)
- HML    : High Minus Low (value vs growth)
- MOM    : Momentum factor (Fama-French 5-factor extension)

These factors explain a large portion of stock returns and add
meaningful predictive signal to the XGBoost model.

Source: Ken French's Data Library via pandas-datareader.
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_ff_cache: Optional[pd.DataFrame] = None
_ff_cache_date: Optional[datetime] = None
_FF_CACHE_DAYS = 7  # refresh weekly (FF data updates monthly)


# ══════════════════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════════════════

def _load_ff_factors() -> Optional[pd.DataFrame]:
    """Load Fama-French 3-Factor + Momentum from Ken French's library."""
    global _ff_cache, _ff_cache_date

    if _ff_cache is not None and _ff_cache_date:
        if (datetime.now() - _ff_cache_date).days < _FF_CACHE_DAYS:
            return _ff_cache

    try:
        import pandas_datareader.data as web

        ff3 = web.DataReader(
            "F-F_Research_Data_Factors_daily",
            "famafrench",
            start="2020-01-01",
        )[0]

        try:
            mom = web.DataReader(
                "F-F_Momentum_Factor_daily",
                "famafrench",
                start="2020-01-01",
            )[0]
            ff3["MOM"] = mom["Mom   "]
        except Exception:
            ff3["MOM"] = 0.0

        # FF data is in % — convert to decimals
        for col in ff3.columns:
            ff3[col] = ff3[col] / 100.0

        ff3.index = pd.to_datetime(ff3.index)
        ff3 = ff3.sort_index()

        _ff_cache = ff3
        _ff_cache_date = datetime.now()
        logger.info("Loaded Fama-French factors: %d rows, cols: %s", len(ff3), list(ff3.columns))
        return ff3

    except ImportError:
        logger.warning("pandas-datareader not installed: pip install pandas-datareader")
        return None
    except Exception as e:
        logger.warning("Failed to load Fama-French data: %s", e)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Per-ticker features for XGBoost
# ══════════════════════════════════════════════════════════════════════════════

def get_ff_features_for_ticker(
    ticker: str,
    lookback_days: int = 252,
) -> Optional[dict]:
    """
    Compute Fama-French factor features for XGBoost training/inference.

    Returns 10 features:
      ff_mkt_avg, ff_smb_avg, ff_hml_avg, ff_mom_avg  — average exposures
      ff_mkt_corr                                       — beta proxy
      ff_recent_smb, ff_recent_hml, ff_recent_mom      — last-20d trend
      ff_value_regime, ff_momentum_regime               — binary regime flags
    """
    try:
        import yfinance as yf
        import numpy as np

        ff = _load_ff_factors()
        if ff is None:
            return None

        hist = yf.Ticker(ticker).history(period=f"{lookback_days + 30}d")["Close"]
        if hist.empty or len(hist) < 30:
            return None

        stock_returns = hist.pct_change().dropna()
        stock_returns.index = stock_returns.index.tz_localize(None)

        ff_aligned = ff.reindex(stock_returns.index, method="ffill").dropna()
        stock_aligned = stock_returns.reindex(ff_aligned.index).dropna()
        ff_aligned = ff_aligned.reindex(stock_aligned.index).dropna()

        if len(ff_aligned) < 20:
            return None

        mkt = ff_aligned["Mkt-RF"].values
        smb = ff_aligned["SMB"].values
        hml = ff_aligned["HML"].values
        mom_col = ff_aligned.get("MOM")
        mom = mom_col.values if mom_col is not None else mkt * 0
        stock = stock_aligned.values

        mkt_corr = float(np.corrcoef(stock, mkt)[0, 1]) if len(stock) > 5 else 0.0
        recent_smb = float(np.mean(smb[-20:])) if len(smb) >= 20 else float(np.mean(smb))
        recent_hml = float(np.mean(hml[-20:])) if len(hml) >= 20 else float(np.mean(hml))
        recent_mom = float(np.mean(mom[-20:])) if len(mom) >= 20 else float(np.mean(mom))

        features = {
            "ff_mkt_avg":        round(float(np.mean(mkt)), 6),
            "ff_smb_avg":        round(float(np.mean(smb)), 6),
            "ff_hml_avg":        round(float(np.mean(hml)), 6),
            "ff_mom_avg":        round(float(np.mean(mom)), 6),
            "ff_mkt_corr":       round(mkt_corr, 4),
            "ff_recent_smb":     round(recent_smb, 6),
            "ff_recent_hml":     round(recent_hml, 6),
            "ff_recent_mom":     round(recent_mom, 6),
            "ff_value_regime":   1 if recent_hml > 0 else 0,
            "ff_momentum_regime": 1 if recent_mom > 0 else 0,
        }

        logger.debug(
            "FF features for %s: corr=%.3f smb=%.4f hml=%.4f mom=%.4f",
            ticker, mkt_corr, recent_smb, recent_hml, recent_mom,
        )
        return features

    except Exception as e:
        logger.debug("FF features failed for %s: %s", ticker, e)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Market regime snapshot for Agent 1
# ══════════════════════════════════════════════════════════════════════════════

def get_current_market_regime_ff() -> Optional[dict]:
    """
    Current Fama-French regime — value vs growth, small vs large cap.
    Used by Agent 1 to enrich regime report.
    """
    try:
        ff = _load_ff_factors()
        if ff is None:
            return None

        recent = ff.tail(20)

        smb_trend = float(recent["SMB"].mean())
        hml_trend = float(recent["HML"].mean())
        mkt_trend = float(recent["Mkt-RF"].mean())

        regime = {
            "smb_20d":          round(smb_trend * 100, 3),
            "hml_20d":          round(hml_trend * 100, 3),
            "mkt_20d":          round(mkt_trend * 100, 3),
            "favors_small_cap": smb_trend > 0,
            "favors_value":     hml_trend > 0,
            "market_positive":  mkt_trend > 0,
        }

        if smb_trend > 0.001:
            regime["smb_note"] = "📊 סביבה מעדיפה Small Cap — מניות קטנות מובילות"
        elif smb_trend < -0.001:
            regime["smb_note"] = "📊 סביבה מעדיפה Large Cap — מניות ענק מובילות"
        else:
            regime["smb_note"] = "📊 SMB ניטרלי — אין יתרון לגודל"

        if hml_trend > 0.001:
            regime["hml_note"] = "📊 סביבת Value — מניות זולות מכות Growth"
        elif hml_trend < -0.001:
            regime["hml_note"] = "📊 סביבת Growth — מניות טכנולוגיה מובילות"
        else:
            regime["hml_note"] = "📊 HML ניטרלי — Value/Growth מאוזן"

        return regime

    except Exception as e:
        logger.debug("FF regime failed: %s", e)
        return None
