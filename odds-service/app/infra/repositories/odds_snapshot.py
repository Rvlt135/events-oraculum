from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.orm_models import OddsSnapshot
from app.domain.time_utils import now_utc
from .base import BaseRepository

logger = structlog.get_logger()


class OddsSnapshotRepository(BaseRepository[OddsSnapshot]):
    def __init__(self, session: AsyncSession):
        super().__init__(OddsSnapshot, session)

    async def create_snapshot(
        self,
        event_id: UUID,
        bookmaker_id: UUID,
        market_type: str,
        outcomes: Dict[str, Any],
        timestamp_source: datetime,
    ) -> UUID:
        snapshot = OddsSnapshot(
            event_id=event_id,
            bookmaker_id=bookmaker_id,
            market_type=market_type,
            outcomes=outcomes,
            timestamp_source=timestamp_source,
            timestamp_ingested=now_utc()
        )
        snapshot = await self.create(snapshot)
        logger.debug(
            "odds_snapshot_created",
            event_id=str(event_id),
            bookmaker_id=str(bookmaker_id),
            market_type=market_type
        )
        return snapshot.id

    async def get_by_event(
        self,
        event_id: UUID,
        market_type: Optional[str] = None,
        limit: int = 100
    ) -> List[OddsSnapshot]:
        query = select(OddsSnapshot).where(OddsSnapshot.event_id == event_id)

        if market_type:
            query = query.where(OddsSnapshot.market_type == market_type)

        query = query.order_by(OddsSnapshot.timestamp_ingested.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_bookmaker(
        self,
        bookmaker_id: UUID,
        from_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[OddsSnapshot]:
        query = select(OddsSnapshot).where(OddsSnapshot.bookmaker_id == bookmaker_id)

        if from_time:
            query = query.where(OddsSnapshot.timestamp_ingested >= from_time)

        query = query.order_by(OddsSnapshot.timestamp_ingested.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_event_and_bookmaker(
        self, event_id: UUID, bookmaker_id: UUID, market_type: str
    ) -> Optional[OddsSnapshot]:
        result = await self.session.execute(
            select(OddsSnapshot)
            .where(
                and_(
                    OddsSnapshot.event_id == event_id,
                    OddsSnapshot.bookmaker_id == bookmaker_id,
                    OddsSnapshot.market_type == market_type
                )
            )
            .order_by(OddsSnapshot.timestamp_ingested.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
