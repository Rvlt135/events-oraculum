from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.recommendation import RecommendationDB, RecommendationCreate, RecommendationResponse

logger = structlog.get_logger()


class RecommendationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, rec: RecommendationCreate) -> RecommendationResponse:
        db_rec = RecommendationDB(
            event_id=rec.event_id,
            league_key=rec.league_key,
            pick=rec.pick,
            confidence=rec.confidence,
            short_explanation=rec.short_explanation,
            model_version=rec.model_version,
            created_ts=datetime.utcnow(),
        )

        self.session.add(db_rec)
        await self.session.commit()
        await self.session.refresh(db_rec)

        logger.info(
            "recommendation_created",
            rec_id=str(db_rec.rec_id),
            event_id=str(rec.event_id),
            pick=rec.pick,
            confidence=rec.confidence,
        )

        return RecommendationResponse.model_validate(db_rec)

    async def get_by_event_id(self, event_id: UUID) -> List[RecommendationResponse]:
        result = await self.session.execute(
            select(RecommendationDB).where(RecommendationDB.event_id == event_id)
        )
        recs = result.scalars().all()
        return [RecommendationResponse.model_validate(rec) for rec in recs]

    async def get_recommendations(
        self,
        league: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100,
    ) -> List[RecommendationResponse]:
        query = select(RecommendationDB)

        filters = []
        if league:
            filters.append(RecommendationDB.league_key == league)
        if from_date:
            filters.append(RecommendationDB.created_ts >= from_date)
        if to_date:
            filters.append(RecommendationDB.created_ts <= to_date)
        if min_confidence is not None:
            filters.append(RecommendationDB.confidence >= min_confidence)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(RecommendationDB.created_ts.desc()).limit(limit)

        result = await self.session.execute(query)
        recs = result.scalars().all()

        return [RecommendationResponse.model_validate(rec) for rec in recs]
