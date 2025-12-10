"""
Service for building team features
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.recommendation import RecommendationResponse, RecommendationCreate
from app.infrastructure.cache import RecommendationCache
from app.infrastructure.repositories.recommendation import  RecommendationRepository
logger = structlog.get_logger()

# TODO: Legacy delete
class RecommendationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: RecommendationCache
    ):
        self.session_factory = session_factory
        self.cache = cache

    # TODO: LEGACY
    async def get_recommendations_by_event(self, session: AsyncSession, event_id: UUID) -> List[RecommendationResponse]:
        repository = RecommendationRepository(session)
        recommendations = await repository.get_by_event_id(event_id)
        return [RecommendationResponse.model_validate(rec) for rec in recommendations]

    async def get_recommendations(self, session: AsyncSession, league: Optional[str] = None, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None,
                                  min_confidence: Optional[float] = None, limit: int = 100):
        repository = RecommendationRepository(session)

        recommendations = await repository.get_recommendations(
            league=league,
            from_date=from_date,
            to_date=to_date,
            min_confidence=min_confidence,
            limit=limit
        )
        return recommendations

    # TODO: LEGACY
    async def save_recommendation(
        self, recommendation: RecommendationCreate
    ) -> RecommendationResponse:
        try:
            async with self.session_factory() as session:
                repository = RecommendationRepository(session)
                saved = await repository.create(recommendation)

                rec_dict = {
                    "rec_id": str(saved.rec_id),
                    "event_id": str(saved.event_id),
                    "league_key": saved.league_key,
                    "pick": saved.pick,
                    "confidence": saved.confidence,
                    "short_explanation": saved.short_explanation,
                    "reasoning": saved.reasoning,
                    "model_version": saved.model_version,
                    "created_ts": saved.created_ts.isoformat(),
                }

                await self.cache.save_recommendation(
                    event_id=saved.event_id,
                    recommendation=rec_dict
                )

                date_key = datetime.utcnow().date().isoformat()
                await self.cache.add_to_list(
                    league=saved.league_key,
                    date_key=date_key,
                    recommendation=rec_dict
                )

            logger.info(
                "recommendation_persisted",
                rec_id=str(saved.rec_id),
                event_id=str(saved.event_id),
                pick=saved.pick
            )

            return saved

        except Exception as e:
            logger.error("persistence_error", error=str(e))
            raise

    async def get_from_cache_or_db(
        self, event_id: UUID
    ) -> RecommendationResponse | None:
        cached = await self.cache.get_recommendation(event_id)
        if cached:
            logger.debug("recommendation_from_cache", event_id=str(event_id))
            return RecommendationResponse(**cached)
        async with self.session_factory() as session:
            repository = RecommendationRepository(session)
            db_rec = await repository.get_by_event_id(event_id)
            if db_rec and len(db_rec) > 0:
                logger.debug("recommendation_from_db", event_id=str(event_id))
                return RecommendationResponse.model_validate(db_rec[0])

        return None
