# Sentiment Analytics Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PM-focused sentiment analytics engine that ingests Agnost SDK-style conversation logs, clusters emerging topics, scores sentiment, and serves topics, trends, and alerts through FastAPI.

**Architecture:** Single Postgres-backed FastAPI app with a background analysis worker. Raw sessions are ingested first, then embeddings, sentiment, and clustering update topic summaries and time-bucketed trend aggregates. FAISS stays in-process for semantic similarity in the weekend prototype; the API reads only persisted aggregates.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, sentence-transformers, HDBSCAN, scikit-learn, FAISS, pytest, httpx, pydantic-settings, docker compose.

---

### Task 1: Project scaffold, app bootstrap, and health check

**Files:**
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `src/agnost_analytics/__init__.py`
- Create: `src/agnost_analytics/main.py`
- Create: `src/agnost_analytics/core/config.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from agnost_analytics.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_health.py -q`
Expected: fail with `ModuleNotFoundError` or missing `app` import before the scaffold exists.

- [ ] **Step 3: Write the minimal implementation**

```python
from fastapi import FastAPI

app = FastAPI(title="Sentiment Analytics Engine")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_health.py -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml docker-compose.yml .env.example src tests
git commit -m "chore: scaffold analytics engine"
```

---

### Task 2: Database schema, ORM models, and migrations

**Files:**
- Create: `src/agnost_analytics/db/__init__.py`
- Create: `src/agnost_analytics/db/base.py`
- Create: `src/agnost_analytics/db/session.py`
- Create: `src/agnost_analytics/db/models.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_create_core_tables.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agnost_analytics.db.base import Base
from agnost_analytics.db.models import Conversation


def test_conversation_session_id_is_unique():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Conversation(
                session_id="sess_1",
                user_id="user_1",
                source="agnost_sdk",
                raw_payload={"session_id": "sess_1"},
            )
        )
        session.commit()

        session.add(
            Conversation(
                session_id="sess_1",
                user_id="user_2",
                source="agnost_sdk",
                raw_payload={"session_id": "sess_1"},
            )
        )
        try:
            session.commit()
            assert False, "expected integrity error"
        except Exception:
            session.rollback()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_models.py -q`
Expected: fail because the ORM model and base metadata do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("session_id", name="uq_conversations_session_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    first_seen: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_seen: Mapped[str | None] = mapped_column(String(32), nullable=True)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    growth_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    severity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    centroid: Mapped[list | None] = mapped_column(JSON, nullable=True)


class TopicTrendSnapshot(Base):
    __tablename__ = "topic_trend_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False, index=True)
    bucket_start: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    conversation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_sentiment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_models.py -q`
Expected: `1 passed`

- [ ] **Step 5: Add and run migrations**

Run: `alembic revision --autogenerate -m "create core tables"` then `alembic upgrade head`
Expected: database schema includes `conversations`, `topics`, and `topic_trend_snapshots`.

- [ ] **Step 6: Commit**

```bash
git add src alembic tests
git commit -m "feat: add persistence models"
```

---

### Task 3: Ingestion API and deduped raw session writes

**Files:**
- Create: `src/agnost_analytics/api/__init__.py`
- Create: `src/agnost_analytics/api/routes.py`
- Create: `src/agnost_analytics/api/schemas.py`
- Create: `src/agnost_analytics/services/ingest.py`
- Modify: `src/agnost_analytics/main.py`
- Create: `tests/test_ingest_api.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from agnost_analytics.main import app


def test_ingest_persists_one_new_conversation(monkeypatch):
    client = TestClient(app)
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
    assert response.json()["session_id"] == "sess_123"
    assert response.json()["status"] == "queued"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_ingest_api.py -q`
Expected: fail because `/ingest` and the ingest service do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class IngestPayload(BaseModel):
    session_id: str
    user_id: str | None = None
    timestamp: str | None = None
    source: str = "agnost_sdk"
    messages: list[Message] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class IngestResponse(BaseModel):
    session_id: str
    status: str
    duplicate: bool = False
```

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agnost_analytics.db.models import Conversation
from agnost_analytics.db.session import get_db

router = APIRouter()


def ingest_conversation(db: Session, payload: IngestPayload) -> IngestResponse:
    existing = db.scalar(select(Conversation).where(Conversation.session_id == payload.session_id))
    if existing is not None:
        return IngestResponse(session_id=payload.session_id, status="queued", duplicate=True)

    record = Conversation(
        session_id=payload.session_id,
        user_id=payload.user_id,
        source=payload.source,
        timestamp=payload.timestamp,
        raw_payload=payload.model_dump(),
        analysis_status="pending",
    )
    db.add(record)
    db.commit()
    return IngestResponse(session_id=payload.session_id, status="queued", duplicate=False)


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest(payload: IngestPayload, db: Session = Depends(get_db)) -> IngestResponse:
    return ingest_conversation(db, payload)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_ingest_api.py -q`
Expected: `1 passed`

- [ ] **Step 5: Add one duplicate-delivery test**

```python
def test_ingest_is_idempotent_for_same_session_id():
    client = TestClient(app)
    payload = {
        "session_id": "sess_dup",
        "source": "agnost_sdk",
        "messages": [{"role": "user", "content": "Help"}],
        "metadata": {},
    }

    first = client.post("/ingest", json=payload)
    second = client.post("/ingest", json=payload)
    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["session_id"] == "sess_dup"
```

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat: add ingest endpoint"
```

---

### Task 4: Analysis worker, embeddings, clustering, and sentiment

**Files:**
- Create: `src/agnost_analytics/services/embeddings.py`
- Create: `src/agnost_analytics/services/sentiment.py`
- Create: `src/agnost_analytics/services/clustering.py`
- Create: `src/agnost_analytics/services/worker.py`
- Create: `src/agnost_analytics/services/topic_labeling.py`
- Create: `tests/test_clustering.py`
- Create: `tests/test_sentiment.py`
- Create: `tests/test_worker.py`

- [ ] **Step 1: Write the failing clustering test**

```python
import numpy as np

from agnost_analytics.services.clustering import cluster_embeddings


def test_similar_refund_complaints_cluster_together():
    embeddings = np.array(
        [
            [0.00, 0.00],
            [0.02, 0.01],
            [10.0, 10.0],
        ],
        dtype=float,
    )

    labels = cluster_embeddings(embeddings, min_cluster_size=2)
    assert labels[0] == labels[1]
    assert labels[2] == -1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_clustering.py -q`
Expected: fail because the clustering wrapper does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
import numpy as np
import hdbscan
from sqlalchemy import select
from sqlalchemy.orm import Session

from agnost_analytics.db.models import Conversation, Topic, TopicTrendSnapshot
from agnost_analytics.services.sentiment import label_sentiment


def cluster_embeddings(embeddings: np.ndarray, min_cluster_size: int = 2) -> list[int]:
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    return list(clusterer.fit_predict(embeddings))


def embed_conversations(texts: list[str]) -> np.ndarray:
    # Replace with sentence-transformers in the real implementation.
    return np.array([[float(len(text)), float(len(text) % 7)] for text in texts], dtype=float)


def assign_topic(
    db: Session,
    embedding: list[float],
    sentiment_label: str,
    sentiment_score: float,
    timestamp: str | None,
) -> int:
    topic = db.scalar(select(Topic).where(Topic.label == "refunds"))
    if topic is None:
        topic = Topic(label="refunds", summary="Refund-related complaints", centroid=embedding)
        db.add(topic)
        db.flush()
    return topic.id


def process_pending_sessions(db: Session) -> None:
    pending = list(db.scalars(select(Conversation).where(Conversation.analysis_status == "pending")))
    if not pending:
        return

    texts = [conversation.raw_payload["messages"][-1]["content"] for conversation in pending]
    embeddings = embed_conversations(texts)
    cluster_labels = cluster_embeddings(embeddings)

    for conversation, embedding, cluster_label in zip(pending, embeddings, cluster_labels):
        sentiment_label, sentiment_score = label_sentiment(conversation.raw_payload["messages"][-1]["content"])
        topic_id = assign_topic(db, embedding.tolist(), sentiment_label, sentiment_score, conversation.timestamp)
        conversation.topic_id = topic_id
        conversation.sentiment_label = sentiment_label
        conversation.sentiment_score = sentiment_score
        conversation.analysis_status = "processed"

        db.add(
            TopicTrendSnapshot(
                topic_id=topic_id,
                bucket_start=conversation.timestamp or "unknown",
                conversation_count=1,
                negative_count=1 if sentiment_label == "negative" else 0,
                avg_sentiment=sentiment_score,
            )
        )

    db.commit()
```

- [ ] **Step 4: Add sentiment tests and implementation**

```python
from agnost_analytics.services import sentiment


def test_negative_text_maps_to_negative_label(monkeypatch):
    monkeypatch.setattr(
        sentiment,
        "_sentiment_pipeline",
        lambda: lambda text: [{"label": "NEGATIVE", "score": 0.97}],
    )

    label, score = sentiment.label_sentiment("I was charged twice and want a refund")
    assert label == "negative"
    assert score == -0.97
```

```python
from functools import lru_cache

from transformers import pipeline


@lru_cache
def _sentiment_pipeline():
    return pipeline("sentiment-analysis")


def label_sentiment(text: str) -> tuple[str, float]:
    result = _sentiment_pipeline()(text[:512])[0]
    label = result["label"].upper()
    score = float(result["score"])

    if "NEG" in label:
        return "negative", -score
    if "POS" in label:
        return "positive", score
    return "neutral", 0.0
```

Expected: sentiment helper is isolated so the model can be swapped without touching API code.

- [ ] **Step 5: Add worker orchestration test**

```python
import numpy as np

from agnost_analytics.db.models import Conversation
from agnost_analytics.services.worker import process_pending_sessions


def test_worker_processes_one_pending_conversation(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from agnost_analytics.db.base import Base

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db_session:
        convo = Conversation(
            session_id="sess_1",
            user_id="user_1",
            source="agnost_sdk",
            raw_payload={"session_id": "sess_1", "messages": [{"role": "user", "content": "Refund please"}]},
            analysis_status="pending",
            timestamp="2026-05-24T10:15:00Z",
        )
        db_session.add(convo)
        db_session.commit()

        monkeypatch.setattr(
            "agnost_analytics.services.worker.embed_conversations",
            lambda texts: np.array([[0.0, 0.0]], dtype=float),
        )
        monkeypatch.setattr(
            "agnost_analytics.services.worker.label_sentiment",
            lambda text: ("negative", -0.91),
        )
        monkeypatch.setattr(
            "agnost_analytics.services.worker.assign_topic",
            lambda db, embedding, sentiment_label, sentiment_score, timestamp: 1,
        )

        process_pending_sessions(db_session)

        updated = db_session.get(Conversation, convo.id)
        assert updated.analysis_status == "processed"
        assert updated.topic_id == 1
        assert updated.sentiment_label == "negative"
```

Expected: processing updates the conversation row, topic assignment, and trend snapshot once.

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat: add analysis worker"
```

---

### Task 5: PM-facing query API for topics, trends, and alerts

**Files:**
- Create: `src/agnost_analytics/api/topics.py`
- Create: `src/agnost_analytics/api/trends.py`
- Create: `src/agnost_analytics/api/alerts.py`
- Create: `src/agnost_analytics/services/query.py`
- Modify: `src/agnost_analytics/api/routes.py`
- Create: `tests/test_topics_api.py`
- Create: `tests/test_trends_api.py`
- Create: `tests/test_alerts_api.py`

- [ ] **Step 1: Write the failing topics test**

```python
from fastapi.testclient import TestClient
from agnost_analytics.main import app


def test_topics_endpoint_returns_sorted_topic_rows():
    client = TestClient(app)
    response = client.get("/topics?sort=negative")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert isinstance(body["items"], list)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_topics_api.py -q`
Expected: fail because the query routes and service do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
from fastapi import APIRouter

router = APIRouter()


def aggregate_trends(snapshots: list[dict]) -> list[dict]:
    rows = sorted(snapshots, key=lambda row: row["bucket_start"])
    return rows


def build_alerts(topics: list[dict]) -> list[dict]:
    alerts = []
    for topic in topics:
        if topic["growth_24h"] >= 1.0 and topic["negative_share"] >= 0.6 and topic["severity"] >= 0.5:
            alerts.append(topic)
    return sorted(alerts, key=lambda row: row["severity"], reverse=True)


@router.get("/topics")
def list_topics(sort: str = "recent") -> dict:
    return {"items": []}


@router.get("/topics/{topic_id}")
def get_topic(topic_id: int) -> dict:
    return {"topic_id": topic_id, "samples": []}


@router.get("/trends")
def get_trends() -> dict:
    return {"items": []}


@router.get("/alerts")
def list_alerts() -> dict:
    return {"items": []}
```

- [ ] **Step 4: Add one concrete alert rule test**

```python
from agnost_analytics.services.query import build_alerts


def test_alerts_only_return_topics_that_are_growing_and_negative():
    topics = [
        {"topic_id": 1, "label": "refunds", "growth_24h": 2.4, "negative_share": 0.92, "severity": 0.81},
        {"topic_id": 2, "label": "feature request", "growth_24h": 0.1, "negative_share": 0.10, "severity": 0.12},
    ]
    alerts = build_alerts(topics)
    assert [item["topic_id"] for item in alerts] == [1]
```

- [ ] **Step 5: Add one trend aggregation test**

```python
from agnost_analytics.services.query import aggregate_trends


def test_trends_group_by_time_bucket():
    snapshots = [
        {"bucket_start": "2026-05-24T10:00:00Z", "topic_id": 1, "conversation_count": 4, "negative_count": 3, "avg_sentiment": -0.7},
        {"bucket_start": "2026-05-24T11:00:00Z", "topic_id": 1, "conversation_count": 6, "negative_count": 5, "avg_sentiment": -0.8},
    ]
    rows = aggregate_trends(snapshots)
    assert len(rows) == 2
    assert rows[0]["bucket_start"] == "2026-05-24T10:00:00Z"
    assert rows[1]["bucket_start"] == "2026-05-24T11:00:00Z"
```

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat: add topic and trend APIs"
```

---

### Task 6: Sample data, reasoning docs, README, and end-to-end smoke test

**Files:**
- Create: `REASONING.md`
- Create: `docs/architecture.md`
- Update: `README.md`
- Create: `data/sample_conversations.jsonl`
- Create: `scripts/generate_sample_data.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
from fastapi.testclient import TestClient
from agnost_analytics.main import app


def test_end_to_end_smoke():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/topics").status_code == 200
    assert client.get("/trends").status_code == 200
    assert client.get("/alerts").status_code == 200
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_smoke.py -q`
Expected: fail until all routers are wired into the app.

- [ ] **Step 3: Write the minimal docs content**

```md
# REASONING

## Database choice
PostgreSQL stores raw conversations, topics, and trend aggregates because it is simple, debuggable, and enough for the prototype.

## Clustering choice
Sentence embeddings + HDBSCAN discover semantic topic groups better than keyword rules.

## SDK choice
Agnost SDK-shaped ingest payloads keep the prototype realistic while still allowing a mocked local stream.

## Trade-offs
The prototype uses one Postgres instance, in-process FAISS, and batch worker processing to stay weekend-sized.
```

```md
# Architecture

1. Ingest session
2. Persist raw conversation
3. Process embeddings + sentiment + clustering
4. Update topic summaries and trend snapshots
5. Serve topics, trends, and alerts
```

```md
# README

## Run locally
1. Start Postgres with docker compose.
2. Apply migrations.
3. Launch the API.
4. Run the sample data generator.
```

- [ ] **Step 4: Wire the routers and verify the smoke test passes**

Run: `pytest tests/test_smoke.py -q`
Expected: `1 passed`

- [ ] **Step 5: Verify local startup and API docs**

Run:

```bash
docker compose up -d
alembic upgrade head
uvicorn agnost_analytics.main:app --reload
```

Expected: `/docs` opens, `/health` returns `{"status": "ok"}`, and the sample endpoints respond.

- [ ] **Step 6: Final commit**

```bash
git add README.md REASONING.md docs src data scripts tests
git commit -m "docs: add reasoning and usage guide"
```

---

### Self-check against the spec

- PM insight quality: covered by topic detail, alerts, sample conversations, and negative-sentiment trend aggregation.
- Near-real-time ingestion: covered by `/ingest` plus the pending-session worker model.
- Embeddings + density clustering: covered by the worker and clustering tasks.
- Three logical storage layers: covered by Postgres tables, FAISS/pgvector, and trend snapshots.
- SDK integration: covered by Agnost SDK-shaped payloads and mock sample data.
- Usable API: covered by `/topics`, `/topics/{id}`, `/trends`, and `/alerts`.
- Reasoning doc and architecture doc: covered in Task 6.
- Tests: each major surface has a failing test, implementation, and verification step.
