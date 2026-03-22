"""XGBoost filter utilities — shared across all scanner pipelines.

Provides:
  enrich_with_confidence(tickers)       → list[(confidence, ticker)]
  filter_by_confidence(ranked, ...)     → filtered list
  get_xgb_label(confidence)             → emoji label string
  build_xgb_summary_block(ranked)       → Telegram-formatted block
  log_scan_candidates(tickers, source)  → records to MongoDB
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def enrich_with_confidence(tickers: list[str]) -> list[tuple[float, str]]:
    """
    Run XGBoost predict_confidence on every ticker.
    Returns list of (confidence, ticker) sorted descending.
    Tickers with no score (OTC / insufficient data) are pushed to the bottom with 0.0.
    """
    from app.services.ml_service import predict_confidence

    scored: list[tuple[float, str]] = []
    unscored: list[str] = []

    for t in tickers:
        conf = predict_confidence(t)
        if conf is not None:
            scored.append((conf, t))
        else:
            unscored.append(t)

    scored.sort(reverse=True)
    return scored + [(0.0, t) for t in unscored]


def filter_by_confidence(
    ranked: list[tuple[float, str]],
    threshold: float = 0.0,
    top_n: Optional[int] = None,
) -> list[tuple[float, str]]:
    """
    Filter to tickers with confidence >= threshold, then trim to top_n.
    threshold=0.0 keeps everything (useful for OTC-style inclusion).
    """
    result = [item for item in ranked if item[0] >= threshold]
    if top_n is not None:
        result = result[:top_n]
    return result


def get_xgb_label(confidence: float) -> str:
    """Return an emoji + label string for a confidence score (0–100)."""
    if confidence >= 70:
        return "🟢 Strong"
    elif confidence >= 50:
        return "🟡 Moderate"
    elif confidence >= 30:
        return "🟠 Weak"
    elif confidence > 0:
        return "🔴 Low"
    else:
        return "⚫ N/A"


def build_xgb_summary_block(ranked: list[tuple[float, str]]) -> str:
    """
    Build a compact Telegram-formatted block.

    Example output:
      🤖 *XGBoost Confidence*
      AAPL   🟢 Strong   (82.3%)
      TSLA   🟡 Moderate (55.1%)
      ...

    Returns empty string if ranked is empty.
    """
    if not ranked:
        return ""

    lines = ["🤖 *XGBoost Confidence*"]
    for conf, ticker in ranked:
        label = get_xgb_label(conf)
        score = f"({conf:.1f}%)" if conf > 0 else ""
        lines.append(f"`{ticker:<6}` {label} {score}".rstrip())

    return "\n".join(lines)


def log_scan_candidates(tickers: list[str], source: str) -> None:
    """Record tickers to MongoDB scanner_candidates collection (fire-and-forget)."""
    if not tickers:
        return
    try:
        from app.data.mongo_client import MongoDB
        MongoDB.save_scanner_candidates(tickers, source)
    except Exception:
        logger.warning(
            "log_scan_candidates failed for source=%s", source, exc_info=True
        )
