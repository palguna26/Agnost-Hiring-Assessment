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
from agnost_analytics.services.query import build_alerts


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


def test_alert_helper_only_returns_growing_negative_topics() -> None:
    alerts = build_alerts(
        [
            {
                "topic_id": 1,
                "label": "Refund delays",
                "summary": "Refunds are taking too long.",
                "volume": 9,
                "growth_24h": 2.4,
                "negative_share": 0.92,
                "severity": 3.2,
            },
            {
                "topic_id": 2,
                "label": "Feature requests",
                "summary": "Users want a dark mode toggle.",
                "volume": 3,
                "growth_24h": 0.2,
                "negative_share": 0.18,
                "severity": 0.3,
            },
        ]
    )

    assert [item["topic_id"] for item in alerts] == [1]
    assert "Negative share" in alerts[0]["explanation"]


def test_alerts_endpoint_returns_alert_items() -> None:
    fixture = _build_test_client_and_db()
    client, db = next(fixture)
    try:
        db.add_all(
            [
                Topic(
                    id=1,
                    label="Refund delays",
                    summary="Refunds are taking too long.",
                    volume=9,
                    growth_24h=2.4,
                    negative_share=0.92,
                    severity=3.2,
                    first_seen="2026-05-24T08:00:00Z",
                    last_seen="2026-05-24T11:00:00Z",
                ),
                Topic(
                    id=2,
                    label="Feature requests",
                    summary="Users want a dark mode toggle.",
                    volume=3,
                    growth_24h=0.2,
                    negative_share=0.18,
                    severity=0.3,
                    first_seen="2026-05-24T07:00:00Z",
                    last_seen="2026-05-24T07:30:00Z",
                ),
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
            ]
        )
        db.commit()

        response = client.get("/alerts?limit=5")
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["topic_id"] == 1
        assert item["representative_snippets"]
        assert item["confidence"] <= 1.0
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
