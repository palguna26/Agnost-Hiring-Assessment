from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import time
from threading import Event
from typing import Sequence

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from agnost_analytics.db.models import Conversation, Topic, TopicTrendSnapshot
from agnost_analytics.services.clustering import cluster_embeddings
from agnost_analytics.services.embeddings import embed_conversations, semantic_signature, _sentence_transformer_model
from agnost_analytics.services.sentiment import label_sentiment
from agnost_analytics.services.topic_labeling import label_topic


@dataclass(slots=True)
class TrendAccumulator:
    conversation_count: int = 0
    negative_count: int = 0
    sentiment_total: float = 0.0

    def add(self, sentiment_score: float, label: str) -> None:
        self.conversation_count += 1
        self.sentiment_total += sentiment_score
        if label == "negative":
            self.negative_count += 1

    @property
    def average_sentiment(self) -> float:
        if self.conversation_count == 0:
            return 0.0
        return self.sentiment_total / self.conversation_count


def _conversation_text(conversation: Conversation) -> str:
    payload = conversation.raw_payload or {}
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(messages, list):
        return ""

    contents: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            contents.append(content.strip())
    return "\n".join(contents)


def _conversation_user_text(conversation: Conversation) -> str:
    payload = conversation.raw_payload or {}
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(messages, list):
        return ""

    contents: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).lower()
        content = message.get("content")
        if role == "user" and isinstance(content, str) and content.strip():
            contents.append(content.strip())

    if contents:
        return "\n".join(contents)

    return _conversation_text(conversation)


def _bucket_start(timestamp: str | None) -> str:
    if not timestamp:
        return "unknown"

    candidate = timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return timestamp

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = parsed.astimezone(UTC)
    bucketed = parsed.replace(minute=0, second=0, microsecond=0)
    return bucketed.strftime("%Y-%m-%dT%H:00:00Z")


def _upsert_topic(
    db: Session,
    *,
    label: str,
    summary: str,
    centroid: Sequence[float],
    topic_count: int,
    negative_count: int,
    latest_timestamp: str | None,
) -> Topic:
    topic = db.scalar(select(Topic).where(Topic.label == label))
    if topic is None:
        topic = Topic(
            label=label,
            summary=summary,
            first_seen=latest_timestamp,
            last_seen=latest_timestamp,
            volume=topic_count,
            negative_share=(negative_count / topic_count) if topic_count else 0.0,
            growth_24h=float(topic_count),
            severity=(negative_count / topic_count) * topic_count if topic_count else 0.0,
            centroid=list(centroid),
        )
        db.add(topic)
        db.flush()
        return topic

    existing_centroid = list(topic.centroid or centroid)
    if len(existing_centroid) != len(centroid):
        existing_centroid = list(centroid)

    total_volume = max(topic.volume, 0) + topic_count
    weighted_centroid = (
        (np.asarray(existing_centroid, dtype=float) * max(topic.volume, 0))
        + (np.asarray(centroid, dtype=float) * topic_count)
    ) / max(total_volume, 1)

    topic.summary = summary
    topic.last_seen = latest_timestamp or topic.last_seen
    topic.first_seen = topic.first_seen or latest_timestamp
    topic.volume = total_volume
    topic.negative_share = (
        ((topic.negative_share * max(topic.volume - topic_count, 0)) + negative_count) / max(total_volume, 1)
    )
    topic.growth_24h = max(topic.growth_24h, float(topic_count))
    topic.severity = topic.negative_share * topic.volume
    topic.centroid = weighted_centroid.tolist()
    db.flush()
    return topic


def _persist_trend_snapshots(db: Session, accumulators: dict[tuple[int, str], TrendAccumulator]) -> None:
    for (topic_id, bucket_start), accumulator in accumulators.items():
        db.add(
            TopicTrendSnapshot(
                topic_id=topic_id,
                bucket_start=bucket_start,
                conversation_count=accumulator.conversation_count,
                negative_count=accumulator.negative_count,
                avg_sentiment=accumulator.average_sentiment,
            )
        )


def _process_cluster(
    db: Session,
    cluster_texts: list[str],
    cluster_embeddings: np.ndarray,
    cluster_conversations: list[Conversation],
    accumulators: dict[tuple[int, str], TrendAccumulator],
) -> None:
    topic_label, topic_summary, _ = label_topic(cluster_texts)
    centroid = cluster_embeddings.mean(axis=0).tolist()
    latest_timestamp = next((conversation.timestamp for conversation in cluster_conversations if conversation.timestamp), None)
    negative_count = 0

    sentiments: list[tuple[str, float]] = []
    for text in cluster_texts:
        sentiment_label, sentiment_score = label_sentiment(text)
        sentiments.append((sentiment_label, sentiment_score))
        if sentiment_label == "negative":
            negative_count += 1

    topic = _upsert_topic(
        db,
        label=topic_label,
        summary=topic_summary,
        centroid=centroid,
        topic_count=len(cluster_conversations),
        negative_count=negative_count,
        latest_timestamp=latest_timestamp,
    )

    for conversation, (sentiment_label, sentiment_score) in zip(cluster_conversations, sentiments):
        conversation.topic_id = topic.id
        conversation.sentiment_label = sentiment_label
        conversation.sentiment_score = sentiment_score
        conversation.analysis_status = "processed"

        bucket = _bucket_start(conversation.timestamp)
        accumulator = accumulators[(topic.id, bucket)]
        accumulator.add(sentiment_score, sentiment_label)


def process_pending_sessions(db: Session, batch_size: int = 100) -> int:
    """Process pending conversations once and persist topic updates."""

    pending = list(
        db.scalars(
            select(Conversation)
            .where(Conversation.analysis_status == "pending")
            .order_by(Conversation.id)
            .limit(batch_size)
        )
    )
    if not pending:
        return 0

    texts = [_conversation_user_text(conversation) for conversation in pending]
    embeddings = embed_conversations(texts)

    if _sentence_transformer_model() is None:
        grouped_by_signature: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for index, text in enumerate(texts):
            grouped_by_signature[semantic_signature(text)].append(index)

        grouped_indices: dict[int, list[int]] = {}
        noise_indices: list[int] = []
        synthetic_cluster_id = 0
        for signature, indices in grouped_by_signature.items():
            if len(indices) < 2:
                noise_indices.extend(indices)
                continue
            grouped_indices[synthetic_cluster_id] = indices
            synthetic_cluster_id += 1
    else:
        cluster_labels = cluster_embeddings(embeddings, min_cluster_size=2)

        grouped_indices = defaultdict(list)
        noise_indices = []
        for index, cluster_label in enumerate(cluster_labels):
            if cluster_label == -1:
                noise_indices.append(index)
            else:
                grouped_indices[cluster_label].append(index)

    accumulators: dict[tuple[int, str], TrendAccumulator] = defaultdict(TrendAccumulator)

    for indices in grouped_indices.values():
        cluster_conversations = [pending[index] for index in indices]
        cluster_texts = [texts[index] for index in indices]
        cluster_vector = np.asarray([embeddings[index] for index in indices], dtype=float)
        _process_cluster(db, cluster_texts, cluster_vector, cluster_conversations, accumulators)

    for index in noise_indices:
        cluster_conversation = [pending[index]]
        cluster_text = [texts[index]]
        cluster_vector = np.asarray([embeddings[index]], dtype=float)
        _process_cluster(db, cluster_text, cluster_vector, cluster_conversation, accumulators)

    _persist_trend_snapshots(db, accumulators)
    db.commit()
    return len(pending)


def run_worker(
    *,
    poll_interval_seconds: float = 5.0,
    batch_size: int = 100,
    stop_event: Event | None = None,
) -> None:
    """Poll the database and process pending sessions until stopped."""

    from agnost_analytics.db.session import SessionLocal

    while stop_event is None or not stop_event.is_set():
        with SessionLocal() as db:
            process_pending_sessions(db, batch_size=batch_size)

        if stop_event is not None and stop_event.is_set():
            break
        time.sleep(poll_interval_seconds)
