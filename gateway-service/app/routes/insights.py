from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.pg import get_session
from app.db.repositories import RecommendationsReadRepo, EventsReadRepo
from app.services.insights_service import InsightsService
from app.models.schemas import RecommendationDTO, EventDTO, PaginatedResponse
from app.security.apikey import verify_api_key
from app.config.settings import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/insights", tags=["Insights"])


@router.get("/recommendations", response_model=PaginatedResponse)
async def get_recommendations(
    league: Optional[str] = Query(default=None),
    from_date: Optional[datetime] = Query(default=None, alias="from"),
    to_date: Optional[datetime] = Query(default=None, alias="to"),
    min_conf: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(verify_api_key),
) -> PaginatedResponse:
    logger.info(
        "get_recommendations_request",
        league=league,
        from_date=from_date,
        to_date=to_date,
        min_conf=min_conf,
        limit=limit,
        offset=offset,
    )

    recommendations_repo = RecommendationsReadRepo(session)
    events_repo = EventsReadRepo(session)
    service = InsightsService(recommendations_repo, events_repo)

    recommendations, total = await service.get_recommendations(
        league=league,
        from_date=from_date,
        to_date=to_date,
        min_confidence=min_conf,
        limit=limit,
        offset=offset,
    )

    return PaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[rec.model_dump() for rec in recommendations],
    )


@router.get("/events/{event_id}", response_model=EventDTO)
async def get_event_details(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(verify_api_key),
) -> EventDTO:
    logger.info("get_event_details_request", event_id=str(event_id))

    recommendations_repo = RecommendationsReadRepo(session)
    events_repo = EventsReadRepo(session)
    service = InsightsService(recommendations_repo, events_repo)

    event = await service.get_event_details(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )

    return event
