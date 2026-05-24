from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agnost_analytics.db.base import Base
from agnost_analytics.db.models import Conversation
from agnost_analytics.db.session import get_db
from agnost_analytics.main import app


@pytest.fixture()
def test_client_and_db() -> Generator[tuple[TestClient, Session], None, None]:
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


def test_ingest_persists_one_new_conversation(test_client_and_db: tuple[TestClient, Session]):
    client, db = test_client_and_db
    payload = {
        "session_id": "sess_123",
        "user_id": "user_456",
        "timestamp": "2026-05-24T10:15:00Z",
        "source": "agnost_sdk",
        "messages": [
            {"role": "user", "content": "Why was I charged twice?"},
            {"role": "assistant", "content": "Let me check that for you."},
        ],
        "metadata": {"app_id": "app_001", "channel": "chat", "tags": ["billing", "refund"]},
    }

    response = client.post("/ingest", json=payload)
    assert response.status_code == 202
    assert response.json() == {"session_id": "sess_123", "status": "queued", "duplicate": False}

    conversation = db.scalar(select(Conversation).where(Conversation.session_id == "sess_123"))
    assert conversation is not None
    assert conversation.analysis_status == "pending"
    assert conversation.raw_payload["session_id"] == "sess_123"
    assert conversation.raw_payload["messages"][0]["content"] == "Why was I charged twice?"


def test_ingest_is_idempotent_for_same_session_id(test_client_and_db: tuple[TestClient, Session]):
    client, db = test_client_and_db
    payload = {
        "session_id": "sess_dup",
        "source": "agnost_sdk",
        "messages": [{"role": "user", "content": "Help"}],
        "metadata": {},
    }

    first = client.post("/ingest", json=payload)
    second = client.post("/ingest", json=payload)

    assert first.status_code == 202
    assert first.json() == {"session_id": "sess_dup", "status": "queued", "duplicate": False}
    assert second.status_code == 202
    assert second.json() == {"session_id": "sess_dup", "status": "queued", "duplicate": True}
    count = db.scalar(select(func.count()).select_from(Conversation).where(Conversation.session_id == "sess_dup"))
    assert count == 1
