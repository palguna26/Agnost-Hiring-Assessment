from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agnost_analytics.db.base import Base
from agnost_analytics.db.models import Conversation, Topic, TopicTrendSnapshot
from agnost_analytics.db.session import get_db
from agnost_analytics.main import app


def _build_test_client_and_db() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSessionLocal()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, db
    finally:
        app.dependency_overrides.clear()
        db.close()


def _load_sample_conversations() -> list[dict[str, object]]:
    sample_path = Path(__file__).resolve().parents[1] / "data" / "sample_conversations.jsonl"
    return [
        json.loads(line)
        for line in sample_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _seed_smoke_data(db: Session) -> None:
    conversations = _load_sample_conversations()
    for index, payload in enumerate(conversations, start=1):
        db.add(
            Conversation(
                session_id=str(payload["session_id"]),
                user_id=str(payload.get("user_id")) if payload.get("user_id") is not None else None,
                source=str(payload.get("source", "agnost_sdk")),
                timestamp=str(payload.get("timestamp")) if payload.get("timestamp") is not None else None,
                raw_payload=payload,
                analysis_status="processed",
                topic_id=1 if index < 3 else 2,
                sentiment_label="negative" if index < 3 else "neutral",
                sentiment_score=-0.9 if index < 3 else 0.1,
            )
        )

    db.add_all(
        [
            Topic(
                id=1,
                label="Refund delays",
                summary="Customers are waiting too long for refunds.",
                volume=18,
                growth_24h=2.4,
                negative_share=0.89,
                severity=3.8,
                first_seen="2026-05-24T08:00:00Z",
                last_seen="2026-05-24T11:00:00Z",
            ),
            Topic(
                id=2,
                label="Dashboard requests",
                summary="Users are asking for dashboard improvements.",
                volume=6,
                growth_24h=0.4,
                negative_share=0.2,
                severity=0.3,
                first_seen="2026-05-24T09:50:00Z",
                last_seen="2026-05-24T10:10:00Z",
            ),
            TopicTrendSnapshot(
                topic_id=1,
                bucket_start="2026-05-24T09:00:00Z",
                conversation_count=8,
                negative_count=7,
                avg_sentiment=-0.75,
            ),
            TopicTrendSnapshot(
                topic_id=1,
                bucket_start="2026-05-24T10:00:00Z",
                conversation_count=10,
                negative_count=8,
                avg_sentiment=-0.82,
            ),
            TopicTrendSnapshot(
                topic_id=2,
                bucket_start="2026-05-24T10:00:00Z",
                conversation_count=6,
                negative_count=1,
                avg_sentiment=0.05,
            ),
        ]
    )
    db.commit()


def test_end_to_end_smoke() -> None:
    fixture = _build_test_client_and_db()
    client, db = next(fixture)
    try:
        _seed_smoke_data(db)

        assert client.get("/health").status_code == 200

        topics_response = client.get("/topics")
        assert topics_response.status_code == 200
        topics_body = topics_response.json()
        assert topics_body["items"]

        trends_response = client.get("/trends")
        assert trends_response.status_code == 200
        trends_body = trends_response.json()
        assert trends_body["items"]

        alerts_response = client.get("/alerts")
        assert alerts_response.status_code == 200
        alerts_body = alerts_response.json()
        assert alerts_body["items"]
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
