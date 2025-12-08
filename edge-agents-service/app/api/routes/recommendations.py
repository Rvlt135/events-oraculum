from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_recommendation_service
from app.infrastructure.db.pg import get_session
from app.infrastructure.repositories.recommendation import RecommendationRepository
from app.domain.entities.recommendation import RecommendationResponse
from app.services.recommendation.service import RecommendationService

router = APIRouter(prefix="/_agents", tags=["Recommendations"])

logger = structlog.get_logger()


@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    league: Optional[str] = Query(default=None),
    from_date: Optional[datetime] = Query(default=None, alias="from"),
    to_date: Optional[datetime] = Query(default=None, alias="to"),
    min_conf: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> List[RecommendationResponse]:
    logger.info(
        "get_recommendations_request",
        league=league,
        from_date=from_date,
        to_date=to_date,
        min_conf=min_conf,
        limit=limit
    )

    repository = RecommendationRepository(session)

    recommendations = await repository.get_recommendations(
        league=league,
        from_date=from_date,
        to_date=to_date,
        min_confidence=min_conf,
        limit=limit
    )

    logger.info("recommendations_returned", count=len(recommendations))

    return recommendations


@router.get("/recommendations/{event_id}", response_model=List[RecommendationResponse])
async def get_recommendations_by_event(
    event_id: UUID,
    service: RecommendationService = Depends(get_recommendation_service),
) -> List[RecommendationResponse]:
    logger.info("get_recommendations_by_event", event_id=str(event_id))

    resp = await service.get_recommendations_by_event(event_id)

    if not resp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recommendations found for event {event_id}"
        )

    logger.info("event_recommendations_returned", event_id=str(event_id), count=len(resp))

    return resp
