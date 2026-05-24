from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from agnost_analytics.db.session import get_db
from agnost_analytics.services.query import get_topic_detail, list_topics

router = APIRouter(tags=["topics"])


@router.get("/topics")
def read_topics(
    sort: str = Query(default="recent"),
    query: str | None = Query(default=None),
    min_volume: int | None = Query(default=None, ge=0),
    min_severity: float | None = Query(default=None, ge=0.0),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    items = list_topics(db, sort=sort, query=query, min_volume=min_volume, min_severity=min_severity)
    return {"items": items}


@router.get("/topics/{topic_id}")
def read_topic(topic_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    detail = get_topic_detail(db, topic_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return detail
