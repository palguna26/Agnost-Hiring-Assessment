from __future__ import annotations

import numpy as np
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from agnost_analytics.db.base import Base
from agnost_analytics.db.models import Conversation, Topic, TopicTrendSnapshot
from agnost_analytics.services.worker import process_pending_sessions


def test_worker_processes_one_pending_conversation(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db_session:
        convo = Conversation(
            session_id="sess_1",
            user_id="user_1",
            source="agnost_sdk",
            raw_payload={
                "session_id": "sess_1",
                "messages": [{"role": "user", "content": "Refund please"}],
            },
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

        processed = process_pending_sessions(db_session)

        updated = db_session.get(Conversation, convo.id)
        topic = db_session.scalar(select(Topic))
        snapshot = db_session.scalar(select(TopicTrendSnapshot))

        assert processed == 1
        assert updated is not None
        assert topic is not None
        assert snapshot is not None
        assert updated.analysis_status == "processed"
        assert updated.topic_id == topic.id
        assert updated.sentiment_label == "negative"
        assert updated.sentiment_score == -0.91
        assert topic.label == "Refund"
        assert topic.volume == 1
        assert snapshot.topic_id == topic.id
        assert snapshot.conversation_count == 1
        assert snapshot.negative_count == 1
        assert snapshot.avg_sentiment == -0.91
