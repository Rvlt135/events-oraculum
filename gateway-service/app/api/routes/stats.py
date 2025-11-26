from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.session import get_session
from app.infrastructure.db.repositories.recommendations_repo import RecommendationsReadRepo
from app.services.stats_service import StatsService
from app.api.schemas.insights import StatsDTO
from app.infrastructure.security.apikey import verify_api_key

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/stats", tags=["Stats"])


@router.get("/summary", response_model=StatsDTO)
async def get_stats_summary(
    league: Optional[str] = Query(default=None),
    from_date: Optional[datetime] = Query(default=None, alias="from"),
    to_date: Optional[datetime] = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(verify_api_key),
) -> StatsDTO:
    logger.info(
        "get_stats_summary_request",
        league=league,
        from_date=from_date,
        to_date=to_date,
    )

    recommendations_repo = RecommendationsReadRepo(session)
    service = StatsService(recommendations_repo)

    stats = await service.get_summary(
        league=league,
        from_date=from_date,
        to_date=to_date,
    )

    return stats

