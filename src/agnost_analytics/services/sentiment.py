from __future__ import annotations

from functools import lru_cache
from typing import Callable


@lru_cache(maxsize=1)
def _sentiment_pipeline() -> Callable[[str], list[dict[str, float | str]]]:
    try:
        from transformers import pipeline
    except Exception:
        return _fallback_pipeline

    try:
        return pipeline("sentiment-analysis")
    except Exception:
        return _fallback_pipeline


def _fallback_pipeline(text: str) -> list[dict[str, float | str]]:
    lowered = text.lower()
    negative_markers = (
        "refund",
        "charged twice",
        "angry",
        "broken",
        "cancel",
        "issue",
        "frustrated",
        "not working",
        "bad",
    )
    positive_markers = (
        "thanks",
        "great",
        "love",
        "appreciate",
        "helpful",
        "works",
        "resolved",
        "happy",
    )

    negative_hits = sum(1 for marker in negative_markers if marker in lowered)
    positive_hits = sum(1 for marker in positive_markers if marker in lowered)

    if negative_hits > positive_hits and negative_hits > 0:
        score = min(0.99, 0.55 + 0.08 * negative_hits)
        return [{"label": "NEGATIVE", "score": float(score)}]
    if positive_hits > negative_hits and positive_hits > 0:
        score = min(0.99, 0.55 + 0.08 * positive_hits)
        return [{"label": "POSITIVE", "score": float(score)}]

    return [{"label": "NEUTRAL", "score": 0.5}]


def label_sentiment(text: str) -> tuple[str, float]:
    """Map text to a coarse sentiment label and signed score."""

    result = _sentiment_pipeline()(text[:512])[0]
    label = str(result["label"]).upper()
    score = float(result["score"])

    if "NEG" in label:
        return "negative", -abs(score)
    if "POS" in label:
        return "positive", abs(score)
    return "neutral", 0.0
