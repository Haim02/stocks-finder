"""ML Service — XGBoost price-prediction feature engineering and inference.

Shared logic used by:
  - train_model.py  (training phase)
  - run_smart_money.py (inference via predict_confidence)

Model predicts probability of a ≥5% gain within 10 trading days.

Feature set (v2 — includes daily sentiment):
  Technical : rsi, price_sma20_ratio, price_sma50_ratio, vol_ratio,
              mom5, mom10, mom20, atr, bb_width
  Sentiment : sent_score, sent_has_data
              (sourced from MongoDB daily_market_sentiment;
               defaults to neutral 5.0 / 0 when no record exists)
"""

import logging
import os

import joblib
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
XGB_MODEL_PATH = os.path.normpath(
    os.path.join(_HERE, "..", "models", "xgb_price_model.pkl")
)

# ── Training / labelling constants ─────────────────────────────────────────
GAIN_THRESHOLD = 0.05   # 5 % gain target
FORWARD_DAYS   = 10     # within 10 trading days

# Technical features (unchanged from v1)
TECHNICAL_FEATURE_COLS = [
    "rsi",
    "price_sma20_ratio",
    "price_sma50_ratio",
    "vol_ratio",
    "mom5",
    "mom10",
    "mom20",
    "atr",
    "bb_width",
]

# Sentiment features added in v2
SENTIMENT_FEATURE_COLS = [
    "sent_score",     # float 1–10 (neutral default = 5.0)
    "sent_has_data",  # 1.0 if an actual LLM score exists, 0.0 otherwise
]

# Full feature list used for training and inference
FEATURE_COLS = TECHNICAL_FEATURE_COLS + SENTIMENT_FEATURE_COLS

# Module-level model cache (avoids reloading on every call)
_model_cache: dict | None = None


# ── Feature engineering ────────────────────────────────────────────────────

def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical ML feature columns to an OHLCV DataFrame (returns a copy)."""
    df = df.copy()
    df["rsi"]               = _compute_rsi(df["Close"])
    df["sma20"]             = df["Close"].rolling(20).mean()
    df["sma50"]             = df["Close"].rolling(50).mean()
    df["vol_avg20"]         = df["Volume"].rolling(20).mean()
    df["price_sma20_ratio"] = df["Close"] / df["sma20"]
    df["price_sma50_ratio"] = df["Close"] / df["sma50"]
    df["vol_ratio"]         = df["Volume"] / df["vol_avg20"]
    df["mom5"]              = df["Close"].pct_change(5)
    df["mom10"]             = df["Close"].pct_change(10)
    df["mom20"]             = df["Close"].pct_change(20)
    df["atr"]               = (df["High"] - df["Low"]).rolling(14).mean() / df["Close"]
    bb_std                  = df["Close"].rolling(20).std()
    df["bb_width"]          = (bb_std * 4) / df["sma20"]
    return df


def add_sentiment_features(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Merge MongoDB daily_market_sentiment into the OHLCV DataFrame.

    For each calendar date in df:
      - If a sentiment record exists in MongoDB → use its score, set has_data=1
      - Otherwise → sent_score=5.0 (neutral), sent_has_data=0

    This means historical training rows without scraped sentiment default to
    neutral, while rows collected going forward carry the real LLM signal.
    The model therefore learns the incremental lift from real sentiment over time.

    Args:
        df     : DataFrame with a DatetimeIndex (yfinance OHLCV format)
        ticker : Stock ticker symbol

    Returns:
        df copy with 'sent_score' and 'sent_has_data' columns added.
    """
    df = df.copy()
    df["sent_score"]    = 5.0   # neutral default
    df["sent_has_data"] = 0.0

    try:
        from app.data.mongo_client import MongoDB
        records = MongoDB.get_sentiment_history(ticker, days=730)
        if not records:
            return df

        # Build a date→score lookup dict
        score_by_date: dict[str, float] = {
            r["date"]: float(r["sentiment_score"]) for r in records
        }

        # Map df DatetimeIndex to YYYY-MM-DD strings and look up scores
        date_strs = df.index.strftime("%Y-%m-%d")
        scores    = pd.array([score_by_date.get(d) for d in date_strs], dtype=object)
        has_data  = pd.array([d in score_by_date for d in date_strs], dtype=bool)

        df.loc[has_data, "sent_score"]    = [score_by_date[d] for d in date_strs[has_data]]
        df.loc[has_data, "sent_has_data"] = 1.0

        n_matched = int(has_data.sum())
        if n_matched:
            logger.debug(
                "Sentiment: %s — %d / %d rows matched", ticker, n_matched, len(df)
            )
    except Exception:
        logger.warning(
            "add_sentiment_features failed for %s — using neutral defaults",
            ticker,
            exc_info=True,
        )

    return df


def label_rows(df: pd.DataFrame) -> pd.Series:
    """
    For every row label 1 if the max Close over the next FORWARD_DAYS
    trading days is >= GAIN_THRESHOLD above today's Close, else 0.
    Rows without enough forward data receive NaN.
    """
    closes = df["Close"].values
    labels = np.full(len(closes), np.nan)
    for i in range(len(closes) - 1):
        future = closes[i + 1 : i + 1 + FORWARD_DAYS]
        if len(future) >= FORWARD_DAYS // 2:
            max_gain = (future.max() - closes[i]) / closes[i]
            labels[i] = 1.0 if max_gain >= GAIN_THRESHOLD else 0.0
    return pd.Series(labels, index=df.index, name="label")


# ── Inference ──────────────────────────────────────────────────────────────

def _load_model() -> dict | None:
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    if not os.path.exists(XGB_MODEL_PATH):
        logger.warning(
            "XGBoost model not found at %s — run train_model.py first.",
            XGB_MODEL_PATH,
        )
        return None
    try:
        _model_cache = joblib.load(XGB_MODEL_PATH)
        logger.info("XGBoost model loaded from %s", XGB_MODEL_PATH)
        return _model_cache
    except Exception:
        logger.exception("Failed to load XGBoost model")
        return None


def predict_confidence(ticker: str) -> float | None:
    """
    Returns the model's estimated probability (0–100 %) that *ticker*
    will gain ≥5 % within the next 10 trading days.

    Uses the feature list stored inside the model file so that old models
    (trained without sentiment) continue to work until retrained.

    Returns None if the model is unavailable or data is insufficient.
    """
    model_data = _load_model()
    if not model_data:
        return None
    try:
        # Use the feature list the model was actually trained on (backward-compat)
        feature_cols = model_data.get("features", FEATURE_COLS)

        stock = yf.Ticker(ticker)
        df    = stock.history(period="3mo")
        if df.empty or len(df) < 60:
            return None

        df = extract_features(df)

        # Only add sentiment features if the model was trained with them
        if "sent_score" in feature_cols:
            df = add_sentiment_features(df, ticker)

        df = df.dropna(subset=feature_cols)
        if df.empty:
            return None

        features = df[feature_cols].iloc[[-1]]
        model    = model_data["model"]
        prob     = float(model.predict_proba(features)[0][1])
        return round(prob * 100, 1)
    except Exception:
        logger.warning("predict_confidence failed for %s", ticker, exc_info=True)
        return None
