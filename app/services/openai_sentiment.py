"""
openai_sentiment.py — Fast Batch Sentiment Scorer
===================================================

Uses OpenAI GPT-4o-mini to score sentiment for multiple tickers
simultaneously before Agent 2's 7-step selection.

Why GPT-4o-mini (not Claude):
- 10× cheaper than Claude for simple classification tasks
- Faster for batch processing (20 tickers at once)
- Perfect for: yes/no sentiment, 1-10 scoring, quick summaries

Output per ticker:
- sentiment_score: 1-10 (1=very bearish, 10=very bullish)
- sentiment_label: "bullish" | "bearish" | "neutral"
- risk_flag: bool (True = skip this ticker)
- reason: str (1 sentence explanation)

Cost estimate: ~20 tickers/day = ~$0.002/day = ~$0.06/month
"""

import logging
import os
import json
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-4o-mini"  # cheapest, fastest for classification
MAX_TOKENS   = 800            # short answers only
BATCH_SIZE   = 10             # tickers per API call


@dataclass
class TickerSentiment:
    ticker: str
    sentiment_score: float    # 1-10
    sentiment_label: str      # "bullish" | "bearish" | "neutral"
    risk_flag: bool           # True = skip (major risk detected)
    reason: str               # 1-sentence explanation
    confidence: float         # 0-1


def score_tickers_batch(tickers: list[str]) -> dict[str, TickerSentiment]:
    """
    Score sentiment for multiple tickers in one OpenAI call.
    Returns dict of ticker → TickerSentiment.
    Tickers that fail get neutral score (5.0) and risk_flag=False.
    """
    if not tickers:
        return {}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — skipping sentiment scoring")
        return {t: _neutral_sentiment(t) for t in tickers}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        logger.error("openai package not installed")
        return {t: _neutral_sentiment(t) for t in tickers}

    results = {}

    # Process in batches
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        batch_results = _score_batch(client, batch)
        results.update(batch_results)

    return results


def _score_batch(client, tickers: list[str]) -> dict[str, TickerSentiment]:
    """Score one batch of tickers."""
    ticker_list = ", ".join(tickers)

    prompt = f"""You are a professional options trader assistant.
For each of these stock tickers: {ticker_list}

Based on your knowledge of these companies and general market conditions,
provide a JSON response with this exact structure (no markdown, no explanation):

{{
  "TICKER1": {{
    "score": 7,
    "label": "bullish",
    "risk_flag": false,
    "reason": "Strong earnings momentum and sector tailwinds",
    "confidence": 0.75
  }},
  "TICKER2": {{
    "score": 3,
    "label": "bearish",
    "risk_flag": true,
    "reason": "Regulatory investigation announced recently",
    "confidence": 0.85
  }}
}}

Rules:
- score: 1-10 (1=very bearish, 5=neutral, 10=very bullish)
- label: exactly "bullish", "bearish", or "neutral"
- risk_flag: true ONLY for major risks (investigations, fraud, bankruptcy, recall)
- reason: one sentence, max 15 words
- confidence: 0.0-1.0

Respond with ONLY the JSON. No other text."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.1,  # low temperature for consistent scoring
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()

        # Clean JSON (remove markdown if present)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        results = {}

        for ticker in tickers:
            if ticker in data:
                d = data[ticker]
                results[ticker] = TickerSentiment(
                    ticker=ticker,
                    sentiment_score=float(d.get("score", 5)),
                    sentiment_label=str(d.get("label", "neutral")),
                    risk_flag=bool(d.get("risk_flag", False)),
                    reason=str(d.get("reason", "")),
                    confidence=float(d.get("confidence", 0.5)),
                )
            else:
                results[ticker] = _neutral_sentiment(ticker)

        logger.info(
            "OpenAI scored %d tickers: %s",
            len(results),
            {t: f"{v.sentiment_score:.0f}/{v.sentiment_label}" for t, v in results.items()},
        )
        return results

    except json.JSONDecodeError as e:
        logger.warning("OpenAI JSON parse failed: %s | raw: %s", e, raw[:200])
        return {t: _neutral_sentiment(t) for t in tickers}
    except Exception as e:
        logger.warning("OpenAI sentiment batch failed: %s", e)
        return {t: _neutral_sentiment(t) for t in tickers}


def _neutral_sentiment(ticker: str) -> TickerSentiment:
    return TickerSentiment(
        ticker=ticker,
        sentiment_score=5.0,
        sentiment_label="neutral",
        risk_flag=False,
        reason="No data available",
        confidence=0.0,
    )


def get_quick_fact(question: str) -> str:
    """
    Ask OpenAI a quick factual question.
    Used as fallback when Perplexity is unavailable.
    Returns empty string on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=200,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise financial market assistant. "
                        "Answer in 2-3 bullet points maximum. "
                        "Keep financial terms in English."
                    ),
                },
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("OpenAI quick fact failed: %s", e)
        return ""
