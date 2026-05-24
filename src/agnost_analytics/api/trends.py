from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from agnost_analytics.db.session import get_db
from agnost_analytics.services.query import list_trend_rows

router = APIRouter(tags=["trends"])


@router.get("/trends")
def read_trends(
    topic_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    items = list_trend_rows(db, topic_id=topic_id)
    return {"items": items}
