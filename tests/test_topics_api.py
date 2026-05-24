from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agnost_analytics.db.base import Base
from agnost_analytics.db.models import Conversation, Topic
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


def test_topics_endpoint_returns_sorted_topic_rows() -> None:
    fixture = _build_test_client_and_db()
    client, db = next(fixture)
    try:
        db.add_all(
            [
                Topic(
                    id=1,
                    label="Refund delays",
                    summary="Customers are waiting too long for refunds.",
                    volume=8,
                    growth_24h=2.4,
                    negative_share=0.88,
                    severity=3.6,
                    first_seen="2026-05-24T08:00:00Z",
                    last_seen="2026-05-24T11:00:00Z",
                ),
                Topic(
                    id=2,
                    label="Feature requests",
                    summary="Users want a dark mode toggle.",
                    volume=3,
                    growth_24h=0.2,
                    negative_share=0.17,
                    severity=0.4,
                    first_seen="2026-05-24T07:00:00Z",
                    last_seen="2026-05-24T07:30:00Z",
                ),
            ]
        )
        db.commit()

        response = client.get("/topics?sort=negative")
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert [item["topic_id"] for item in body["items"]] == [1, 2]

        filtered = client.get("/topics?query=refund&min_volume=5")
        assert filtered.status_code == 200
        filtered_items = filtered.json()["items"]
        assert len(filtered_items) == 1
        assert filtered_items[0]["label"] == "Refund delays"
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def test_topic_detail_returns_pm_friendly_fields() -> None:
    fixture = _build_test_client_and_db()
    client, db = next(fixture)
    try:
        topic = Topic(
            id=1,
            label="Refund delays",
            summary="Customers are waiting too long for refunds.",
            volume=2,
            growth_24h=1.5,
            negative_share=1.0,
            severity=1.8,
            first_seen="2026-05-24T08:00:00Z",
            last_seen="2026-05-24T11:00:00Z",
        )
        db.add(topic)
        db.add_all(
            [
                Conversation(
                    session_id="sess_1",
                    user_id="user_1",
                    source="agnost_sdk",
                    timestamp="2026-05-24T10:00:00Z",
                    raw_payload={"messages": [{"role": "user", "content": "I need my refund now"}]},
                    analysis_status="processed",
                    topic_id=1,
                    sentiment_label="negative",
                    sentiment_score=-0.9,
                ),
                Conversation(
                    session_id="sess_2",
                    user_id="user_2",
                    source="agnost_sdk",
                    timestamp="2026-05-24T10:30:00Z",
                    raw_payload={"messages": [{"role": "user", "content": "Still waiting for the refund"}]},
                    analysis_status="processed",
                    topic_id=1,
                    sentiment_label="negative",
                    sentiment_score=-0.8,
                ),
            ]
        )
        db.commit()

        response = client.get("/topics/1")
        assert response.status_code == 200
        body = response.json()
        assert body["topic_id"] == 1
        assert body["label"] == "Refund delays"
        assert body["summary"].startswith("Customers are waiting")
        assert body["sentiment_distribution"] == {"positive": 0, "neutral": 0, "negative": 2}
        assert len(body["representative_conversations"]) == 2
        assert len(body["growth_curve"]) == 0
        assert "refund" in body["keywords"]
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
