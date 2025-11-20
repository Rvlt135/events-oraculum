from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.odds import OddsSnapshot
from app.domain.entities.odds_models.odds import OddsSnapshotDTO, OddsOutcomeDTO
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class OddsSnapshotRepository(BaseRepository[OddsSnapshot]):
    def __init__(self, session: AsyncSession):
        super().__init__(OddsSnapshot, session)

    async def upsert_snapshot(self, dto: OddsSnapshotDTO) -> UUID:
        """
        Upsert snapshot by key (event_id, bookmaker_id, market_type).

        Key: (event_id, bookmaker_id, market_type) - unique constraint.

        Behavior:
        - If record exists: UPDATE outcomes, timestamp_source, timestamp_ingested
        - If not exists: INSERT new record
        - created_at is preserved on update (not touched)

        MVP: Stores only one "current" record per event+bookmaker+market.
        TODO: Future historization - could store multiple versions with timestamps.

        Args:
            dto: OddsSnapshotDTO (id and created_at can be None for new records)

        Returns:
            UUID of snapshot (existing or newly created)
        """
        outcomes_dict = {
            "outcomes": [outcome.model_dump(mode="json") for outcome in dto.outcomes]
        }

        stmt = (
            insert(OddsSnapshot)
            .values(
                event_id=dto.event_id,
                bookmaker_id=dto.bookmaker_id,
                market_type=dto.market_type,
                outcomes=outcomes_dict,
                timestamp_source=dto.timestamp_source,
                timestamp_ingested=dto.timestamp_ingested,
            )
            .on_conflict_do_update(
                index_elements=["event_id", "bookmaker_id", "market_type"],
                set_=dict(
                    outcomes=outcomes_dict,
                    timestamp_source=dto.timestamp_source,
                    timestamp_ingested=dto.timestamp_ingested,
                )
            )
            .returning(OddsSnapshot.id)
        )

        result = await self.session.execute(stmt)
        snapshot_id = result.scalar_one()
        await self.session.flush()

        logger.debug(
            "odds_snapshot_upserted",
            event_id=str(dto.event_id),
            bookmaker_id=str(dto.bookmaker_id),
            market_type=dto.market_type,
            snapshot_id=str(snapshot_id)
        )

        return snapshot_id

    async def create_snapshot(
        self,
        event_id: UUID,
        bookmaker_id: UUID,
        market_type: str,
        outcomes: Dict[str, Any],
        timestamp_source: datetime,
    ) -> UUID:
        """Deprecated: Use upsert_snapshot with OddsSnapshotDTO instead."""
        outcomes_list = outcomes.get("outcomes", []) if isinstance(outcomes, dict) else outcomes
        outcomes_dto = [
            OddsOutcomeDTO(**outcome) if isinstance(outcome, dict) else outcome
            for outcome in outcomes_list
        ]
        dto = OddsSnapshotDTO(
            id=None,
            event_id=event_id,
            bookmaker_id=bookmaker_id,
            market_type=market_type,
            outcomes=outcomes_dto,
            timestamp_source=timestamp_source,
            timestamp_ingested=now_utc(),
            created_at=None,
        )
        return await self.upsert_snapshot(dto)

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
