from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.entities.recommendation import RecommendationResponse, RecommendationCreate
from app.infrastructure.db.orm.recommendation import RecommendationORM

logger = structlog.get_logger()


class RecommendationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, rec: RecommendationCreate) -> RecommendationResponse:
        db_rec = RecommendationORM(
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
        # TODO: Legacy code
        return RecommendationResponse.model_validate(db_rec)

    async def get_by_event_id(self, event_id: UUID) -> List[RecommendationORM]:
        result = await self.session.execute(
            select(RecommendationORM).where(RecommendationORM.event_id == event_id)
        )
        recs = result.scalars().all()
        return [i for i in recs]

    async def get_recommendations(
        self,
        league: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100,
    ) -> List[RecommendationResponse]:
        query = select(RecommendationORM)

        filters = []
        if league:
            filters.append(RecommendationORM.league_key == league)
        if from_date:
            filters.append(RecommendationORM.created_ts >= from_date)
        if to_date:
            filters.append(RecommendationORM.created_ts <= to_date)
        if min_confidence is not None:
            filters.append(RecommendationORM.confidence >= min_confidence)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(RecommendationORM.created_ts.desc()).limit(limit)

        result = await self.session.execute(query)
        recs = result.scalars().all()

        return [RecommendationResponse.model_validate(rec) for rec in recs]
