from __future__ import annotations

from functools import lru_cache
from typing import Callable


REQUEST_MARKERS = (
    "can you add",
    "could you add",
    "please add",
    "would like",
    "i would like",
    "i'd like",
    "feature request",
    "add dark mode",
    "add theme",
    "wish there was",
    "it would be nice",
)

COMPLAINT_MARKERS = (
    "refund",
    "charged twice",
    "duplicate charge",
    "broken",
    "not working",
    "error",
    "bug",
    "frustrated",
    "cancel",
    "problem",
    "trouble",
)

POSITIVE_MARKERS = (
    "thanks",
    "great",
    "love",
    "appreciate",
    "helpful",
    "works",
    "resolved",
    "fixed",
    "happy",
)


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
    negative_hits = sum(1 for marker in COMPLAINT_MARKERS if marker in lowered)
    positive_hits = sum(1 for marker in POSITIVE_MARKERS if marker in lowered)

    if negative_hits > positive_hits and negative_hits > 0:
        score = min(0.99, 0.55 + 0.08 * negative_hits)
        return [{"label": "NEGATIVE", "score": float(score)}]
    if positive_hits > negative_hits and positive_hits > 0:
        score = min(0.99, 0.55 + 0.08 * positive_hits)
        return [{"label": "POSITIVE", "score": float(score)}]

    return [{"label": "NEUTRAL", "score": 0.5}]


def label_sentiment(text: str) -> tuple[str, float]:
    """Map text to a coarse sentiment label and signed score."""

    lowered = text.lower()
    if any(marker in lowered for marker in REQUEST_MARKERS) and not any(
        marker in lowered for marker in COMPLAINT_MARKERS
    ):
        return "neutral", 0.0

    if any(marker in lowered for marker in COMPLAINT_MARKERS):
        return "negative", -0.97

    if any(marker in lowered for marker in POSITIVE_MARKERS):
        return "positive", 0.84

    result = _sentiment_pipeline()(text[:512])[0]
    label = str(result["label"]).upper()
    score = float(result["score"])

    if "NEG" in label:
        return "negative", -abs(score)
    if "POS" in label:
        return "positive", abs(score)
    return "neutral", 0.0
