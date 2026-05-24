from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agnost_analytics.db.base import Base
from agnost_analytics.db.models import Topic, TopicTrendSnapshot
from agnost_analytics.db.session import get_db
from agnost_analytics.main import app
from agnost_analytics.services.query import aggregate_trend_rows


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


def test_trend_helper_aggregates_duplicate_buckets() -> None:
    rows = aggregate_trend_rows(
        [
            {
                "topic_id": 1,
                "bucket_start": "2026-05-24T10:00:00Z",
                "conversation_count": 4,
                "negative_count": 3,
                "avg_sentiment": -0.7,
            },
            {
                "topic_id": 1,
                "bucket_start": "2026-05-24T10:00:00Z",
                "conversation_count": 6,
                "negative_count": 5,
                "avg_sentiment": -0.8,
            },
        ]
    )

    assert len(rows) == 1
    assert rows[0]["conversation_count"] == 10
    assert rows[0]["negative_count"] == 8
    assert rows[0]["negative_share"] == 0.8
    assert round(rows[0]["avg_sentiment"], 2) == -0.76


def test_trends_endpoint_returns_bucketed_rows() -> None:
    fixture = _build_test_client_and_db()
    client, db = next(fixture)
    try:
        db.add(
            Topic(
                id=1,
                label="Refund delays",
                summary="Customers are waiting too long for refunds.",
                volume=10,
                growth_24h=2.1,
                negative_share=0.9,
                severity=4.0,
                first_seen="2026-05-24T08:00:00Z",
                last_seen="2026-05-24T11:00:00Z",
            )
        )
        db.add_all(
            [
                TopicTrendSnapshot(
                    topic_id=1,
                    bucket_start="2026-05-24T10:00:00Z",
                    conversation_count=4,
                    negative_count=3,
                    avg_sentiment=-0.7,
                ),
                TopicTrendSnapshot(
                    topic_id=1,
                    bucket_start="2026-05-24T11:00:00Z",
                    conversation_count=6,
                    negative_count=5,
                    avg_sentiment=-0.8,
                ),
            ]
        )
        db.commit()

        response = client.get("/trends?topic_id=1")
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert len(body["items"]) == 2
        assert body["items"][0]["label"] == "Refund delays"
        assert body["items"][0]["bucket_start"] == "2026-05-24T10:00:00Z"
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
