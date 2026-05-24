from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from agnost_analytics.db.models import Conversation, Topic, TopicTrendSnapshot

ALERT_GROWTH_THRESHOLD = 1.0
ALERT_NEGATIVE_SHARE_THRESHOLD = 0.6
ALERT_SEVERITY_THRESHOLD = 0.5
DEFAULT_ALERT_LIMIT = 10

_STOPWORDS = {
    "a",
    "about",
    "after",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "show",
    "the",
    "this",
    "to",
    "was",
    "we",
    "what",
    "why",
    "with",
    "you",
}


def _row_get(row: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(key, default)
    return getattr(row, key, default)


def _topic_to_dict(topic: Topic) -> dict[str, Any]:
    return {
        "topic_id": topic.id,
        "label": topic.label,
        "summary": topic.summary,
        "volume": topic.volume,
        "growth_24h": topic.growth_24h,
        "negative_share": topic.negative_share,
        "first_seen": topic.first_seen,
        "last_seen": topic.last_seen,
        "severity": topic.severity,
    }


def _conversation_snippet(conversation: Conversation, limit: int = 160) -> str:
    payload = conversation.raw_payload or {}
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(messages, list):
        return ""

    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).lower()
        content = message.get("content")
        if role != "user":
            continue
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())

    snippet = " ".join(parts).strip()
    if not snippet:
        for message in messages:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                snippet = content.strip()
                break
    return snippet[:limit]


def _extract_keywords(text: str, limit: int = 5) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    keywords: list[str] = []
    for token in tokens:
        if len(token) < 3 or token in _STOPWORDS or token in keywords:
            continue
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def sort_topic_rows(rows: Iterable[Mapping[str, Any] | Any], sort: str = "recent") -> list[dict[str, Any]]:
    normalized = [dict(row) if isinstance(row, Mapping) else dict(row.__dict__) for row in rows]

    sort_key = (sort or "recent").lower()
    if sort_key == "volume":
        key_fn = lambda row: (-float(row.get("volume", 0)), -float(row.get("growth_24h", 0.0)), -float(row.get("severity", 0.0)))
    elif sort_key == "growth":
        key_fn = lambda row: (-float(row.get("growth_24h", 0.0)), -float(row.get("severity", 0.0)), -float(row.get("volume", 0)))
    elif sort_key == "negative":
        key_fn = lambda row: (-float(row.get("negative_share", 0.0)), -float(row.get("severity", 0.0)), -float(row.get("volume", 0)))
    elif sort_key == "severity":
        key_fn = lambda row: (-float(row.get("severity", 0.0)), -float(row.get("growth_24h", 0.0)), -float(row.get("volume", 0)))
    else:
        key_fn = lambda row: (
            row.get("last_seen") is not None,
            row.get("last_seen") or "",
            float(row.get("volume", 0)),
            float(row.get("severity", 0.0)),
        )

    if sort_key == "recent":
        return sorted(normalized, key=key_fn, reverse=True)
    return sorted(normalized, key=key_fn)


def filter_topic_rows(
    rows: Iterable[Mapping[str, Any] | Any],
    *,
    query: str | None = None,
    min_volume: int | None = None,
    min_severity: float | None = None,
) -> list[dict[str, Any]]:
    normalized = [dict(row) if isinstance(row, Mapping) else dict(row.__dict__) for row in rows]
    text_query = query.lower().strip() if query else None

    filtered: list[dict[str, Any]] = []
    for row in normalized:
        if min_volume is not None and int(row.get("volume", 0)) < min_volume:
            continue
        if min_severity is not None and float(row.get("severity", 0.0)) < min_severity:
            continue
        if text_query:
            haystack = " ".join(
                str(row.get(field, "")) for field in ("label", "summary", "topic_id")
            ).lower()
            if text_query not in haystack:
                continue
        filtered.append(row)
    return filtered


def aggregate_trend_rows(rows: Iterable[Mapping[str, Any] | Any]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, Any], dict[str, Any]] = {}

    for row in rows:
        topic_id = _row_get(row, "topic_id")
        bucket_start = _row_get(row, "bucket_start")
        key = (topic_id, bucket_start)
        conversation_count = int(_row_get(row, "conversation_count", 0))
        negative_count = int(_row_get(row, "negative_count", 0))
        avg_sentiment = float(_row_get(row, "avg_sentiment", 0.0))

        if key not in grouped:
            grouped[key] = {
                "topic_id": topic_id,
                "bucket_start": bucket_start,
                "conversation_count": 0,
                "negative_count": 0,
                "sentiment_total": 0.0,
                "avg_sentiment": 0.0,
                "negative_share": 0.0,
            }

        grouped_row = grouped[key]
        grouped_row["conversation_count"] += conversation_count
        grouped_row["negative_count"] += negative_count
        grouped_row["sentiment_total"] += avg_sentiment * conversation_count

    aggregated: list[dict[str, Any]] = []
    for grouped_row in grouped.values():
        conversation_count = grouped_row["conversation_count"]
        if conversation_count:
            grouped_row["avg_sentiment"] = grouped_row["sentiment_total"] / conversation_count
            grouped_row["negative_share"] = grouped_row["negative_count"] / conversation_count
        grouped_row.pop("sentiment_total", None)
        aggregated.append(grouped_row)

    aggregated.sort(key=lambda row: (row["bucket_start"], row["topic_id"]))
    return aggregated


def build_alerts(topics: Iterable[Mapping[str, Any] | Any], limit: int = DEFAULT_ALERT_LIMIT) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for topic in topics:
        row = dict(topic) if isinstance(topic, Mapping) else dict(topic.__dict__)
        growth_24h = float(row.get("growth_24h", 0.0))
        negative_share = float(row.get("negative_share", 0.0))
        severity = float(row.get("severity", 0.0))
        volume = int(row.get("volume", 0))

        if (
            growth_24h < ALERT_GROWTH_THRESHOLD
            or negative_share < ALERT_NEGATIVE_SHARE_THRESHOLD
            or severity < ALERT_SEVERITY_THRESHOLD
        ):
            continue

        confidence = min(1.0, round((negative_share * 0.6) + min(growth_24h, 5.0) / 10.0, 2))
        alerts.append(
            {
                "topic_id": row.get("topic_id"),
                "label": row.get("label", ""),
                "summary": row.get("summary", ""),
                "volume": volume,
                "growth_24h": growth_24h,
                "negative_share": negative_share,
                "severity": severity,
                "confidence": confidence,
                "explanation": (
                    f"Negative share is {negative_share:.0%} and growth is {growth_24h:.1f}x, "
                    f"which makes this topic worth attention."
                ),
                "representative_snippets": list(row.get("representative_snippets", [])),
            }
        )

    alerts.sort(key=lambda row: (-row["severity"], -row["growth_24h"], row["topic_id"]))
    return alerts[:limit]


def list_topics(
    db: Session,
    *,
    sort: str = "recent",
    query: str | None = None,
    min_volume: int | None = None,
    min_severity: float | None = None,
) -> list[dict[str, Any]]:
    topics = list(db.scalars(select(Topic)))
    rows = [_topic_to_dict(topic) for topic in topics]
    rows = filter_topic_rows(rows, query=query, min_volume=min_volume, min_severity=min_severity)
    return sort_topic_rows(rows, sort=sort)


def _topic_sentiment_distribution(conversations: Iterable[Conversation]) -> dict[str, int]:
    distribution = {"positive": 0, "neutral": 0, "negative": 0}
    for conversation in conversations:
        label = (conversation.sentiment_label or "neutral").lower()
        if label not in distribution:
            label = "neutral"
        distribution[label] += 1
    return distribution


def get_topic_detail(db: Session, topic_id: int, sample_limit: int = 3) -> dict[str, Any] | None:
    topic = db.scalar(select(Topic).where(Topic.id == topic_id))
    if topic is None:
        return None

    conversations = list(
        db.scalars(
            select(Conversation)
            .where(Conversation.topic_id == topic_id)
            .order_by(Conversation.id.desc())
            .limit(sample_limit)
        )
    )
    snapshots = list(
        db.scalars(
            select(TopicTrendSnapshot)
            .where(TopicTrendSnapshot.topic_id == topic_id)
            .order_by(TopicTrendSnapshot.bucket_start.asc())
        )
    )

    representative_conversations = [
        {
            "conversation_id": conversation.id,
            "session_id": conversation.session_id,
            "timestamp": conversation.timestamp,
            "sentiment_label": conversation.sentiment_label or "neutral",
            "sentiment_score": conversation.sentiment_score,
            "snippet": _conversation_snippet(conversation),
        }
        for conversation in conversations
    ]

    trend_curve = aggregate_trend_rows(
        {
            "topic_id": snapshot.topic_id,
            "bucket_start": snapshot.bucket_start,
            "conversation_count": snapshot.conversation_count,
            "negative_count": snapshot.negative_count,
            "avg_sentiment": snapshot.avg_sentiment,
        }
        for snapshot in snapshots
    )

    detail = _topic_to_dict(topic)
    detail.update(
        {
            "keywords": _extract_keywords(f"{topic.label} {topic.summary}"),
            "sentiment_distribution": _topic_sentiment_distribution(conversations),
            "growth_curve": trend_curve,
            "representative_conversations": representative_conversations,
            "representative_snippets": [item["snippet"] for item in representative_conversations if item["snippet"]],
        }
    )
    return detail


def list_trend_rows(db: Session, topic_id: int | None = None) -> list[dict[str, Any]]:
    stmt = select(TopicTrendSnapshot)
    if topic_id is not None:
        stmt = stmt.where(TopicTrendSnapshot.topic_id == topic_id)

    snapshots = list(db.scalars(stmt))
    rows = aggregate_trend_rows(
        {
            "topic_id": snapshot.topic_id,
            "bucket_start": snapshot.bucket_start,
            "conversation_count": snapshot.conversation_count,
            "negative_count": snapshot.negative_count,
            "avg_sentiment": snapshot.avg_sentiment,
        }
        for snapshot in snapshots
    )

    topic_labels = {
        topic.id: topic.label
        for topic in db.scalars(select(Topic).where(Topic.id.in_({row["topic_id"] for row in rows}))).all()
    }

    for row in rows:
        topic_label = topic_labels.get(row["topic_id"])
        if topic_label:
            row["label"] = topic_label
    return rows


def list_alert_rows(db: Session, limit: int = DEFAULT_ALERT_LIMIT) -> list[dict[str, Any]]:
    topics = list_topics(db, sort="severity")
    enriched_topics = []
    for topic in topics:
        detail = get_topic_detail(db, int(topic["topic_id"]))
        if detail is None:
            continue
        enriched_topic = dict(topic)
        enriched_topic["representative_snippets"] = detail["representative_snippets"]
        enriched_topics.append(enriched_topic)
    return build_alerts(enriched_topics, limit=limit)
