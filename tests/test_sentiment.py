from __future__ import annotations

from agnost_analytics.services import sentiment


def test_negative_text_maps_to_negative_label(monkeypatch) -> None:
    monkeypatch.setattr(
        sentiment,
        "_sentiment_pipeline",
        lambda: lambda text: [{"label": "NEGATIVE", "score": 0.97}],
    )

    label, score = sentiment.label_sentiment("I was charged twice and want a refund")
    assert label == "negative"
    assert score == -0.97


def test_positive_text_maps_to_positive_label(monkeypatch) -> None:
    monkeypatch.setattr(
        sentiment,
        "_sentiment_pipeline",
        lambda: lambda text: [{"label": "POSITIVE", "score": 0.84}],
    )

    label, score = sentiment.label_sentiment("Thanks, that was helpful")
    assert label == "positive"
    assert score == 0.84


def test_neutral_text_maps_to_neutral_label(monkeypatch) -> None:
    monkeypatch.setattr(
        sentiment,
        "_sentiment_pipeline",
        lambda: lambda text: [{"label": "NEUTRAL", "score": 0.51}],
    )

    label, score = sentiment.label_sentiment("Please update my account profile")
    assert label == "neutral"
    assert score == 0.0
