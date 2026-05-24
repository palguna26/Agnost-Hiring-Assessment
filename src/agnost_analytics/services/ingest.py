from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agnost_analytics.api.schemas import IngestPayload, IngestResponse
from agnost_analytics.db.models import Conversation


def ingest_conversation(db: Session, payload: IngestPayload) -> IngestResponse:
    existing = db.scalar(select(Conversation).where(Conversation.session_id == payload.session_id))
    if existing is not None:
        return IngestResponse(session_id=payload.session_id, status="queued", duplicate=True)

    conversation = Conversation(
        session_id=payload.session_id,
        user_id=payload.user_id,
        source=payload.source,
        timestamp=payload.timestamp,
        raw_payload=payload.model_dump(mode="json"),
        analysis_status="pending",
    )

    db.add(conversation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return IngestResponse(session_id=payload.session_id, status="queued", duplicate=True)

    return IngestResponse(session_id=payload.session_id, status="queued", duplicate=False)

