from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from agnost_analytics.api.alerts import router as alerts_router
from agnost_analytics.api.schemas import IngestPayload, IngestResponse
from agnost_analytics.api.topics import router as topics_router
from agnost_analytics.api.trends import router as trends_router
from agnost_analytics.db.session import get_db
from agnost_analytics.services.ingest import ingest_conversation

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest(payload: IngestPayload, db: Session = Depends(get_db)) -> IngestResponse:
    return ingest_conversation(db, payload)


router.include_router(topics_router)
router.include_router(trends_router)
router.include_router(alerts_router)
