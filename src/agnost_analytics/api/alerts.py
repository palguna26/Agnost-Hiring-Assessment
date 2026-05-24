from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from agnost_analytics.db.session import get_db
from agnost_analytics.services.query import list_alert_rows

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def read_alerts(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    items = list_alert_rows(db, limit=limit)
    return {"items": items}
