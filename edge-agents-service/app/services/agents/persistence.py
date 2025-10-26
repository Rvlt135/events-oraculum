from datetime import datetime, date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.recommendation import RecommendationDB, RecommendationCreate, RecommendationResponse
from app.db.repositories import RecommendationRepository
from app.cache.redis import RecommendationCache

logger = structlog.get_logger()


class RecommendationPersistence:
    def __init__(self, session: AsyncSession, cache: RecommendationCache):
        self.session = session
        self.cache = cache
        self.repository = RecommendationRepository(session)

    async def save_recommendation(
        self, recommendation: RecommendationCreate
    ) -> RecommendationResponse:
        try:
            saved = await self.repository.create(recommendation)

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

        db_rec = await self.repository.get_by_event_id(event_id)
        if db_rec and len(db_rec) > 0:
            logger.debug("recommendation_from_db", event_id=str(event_id))
            return db_rec[0]

        return None
