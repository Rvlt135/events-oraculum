from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
import structlog

from app.db.repositories import RecommendationsReadRepo, EventsReadRepo
from app.cache.redis import redis_cache_manager
from app.models.schemas import RecommendationDTO, EventDTO, OddsContextDTO

logger = structlog.get_logger()


class InsightsService:
    def __init__(
        self,
        recommendations_repo: RecommendationsReadRepo,
        events_repo: EventsReadRepo,
    ):
        self.recommendations_repo = recommendations_repo
        self.events_repo = events_repo

    async def get_recommendations(
        self,
        league: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[RecommendationDTO], int]:
        recommendations, total = await self.recommendations_repo.get_recommendations(
            league=league,
            from_date=from_date,
            to_date=to_date,
            min_confidence=min_confidence,
            limit=limit,
            offset=offset,
        )

        dtos = [RecommendationDTO(**rec) for rec in recommendations]

        logger.info(
            "recommendations_retrieved",
            count=len(dtos),
            total=total,
            league=league,
        )

        return dtos, total

    async def get_event_details(self, event_id: UUID) -> Optional[EventDTO]:
        cache_key = f"event:{event_id}"
        cached = await redis_cache_manager.get(cache_key)

        if cached:
            logger.info("event_from_cache", event_id=str(event_id))
            return EventDTO(**cached)

        event = await self.events_repo.get_event(event_id)
        if not event:
            return None

        recommendations_data = await self.recommendations_repo.get_by_event_id(event_id)
        recommendations = [RecommendationDTO(**rec) for rec in recommendations_data]

        odds_context_data = await self.events_repo.get_odds_context(event_id)
        odds_context = OddsContextDTO(**odds_context_data) if odds_context_data else None

        event_dto = EventDTO(
            **event,
            recommendations=recommendations,
            odds_context=odds_context,
        )

        await redis_cache_manager.set(cache_key, event_dto.model_dump(mode="json"))

        logger.info("event_details_retrieved", event_id=str(event_id))

        return event_dto
