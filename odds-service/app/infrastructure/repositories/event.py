from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.events import Event
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession):
        super().__init__(Event, session)

    async def create_or_update(
        self,
        external_id: str,
        sport_id: UUID,
        competition_id: UUID,
        home_team_id: UUID,
        away_team_id: UUID,
        commence_time: datetime,
        status: str,
        event_metadata: Dict[str, Any],
    ) -> UUID:
        result = await self.session.execute(
            select(Event).where(Event.external_id == external_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            event = Event(
                external_id=external_id,
                sport_id=sport_id,
                competition_id=competition_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                commence_time=commence_time,
                status=status,
                metadata=event_metadata
            )
            event = await self.create(event)
            logger.info("event_created", external_id=external_id, id=str(event.id))
        else:
            event.commence_time = commence_time
            event.status = status
            event.metadata = event_metadata
            event.updated_at = now_utc()
            await self.session.flush()
            logger.debug("event_updated", external_id=external_id, id=str(event.id))

        return event.id

    async def get_by_external_id(self, external_id: str) -> Optional[Event]:
        result = await self.session.execute(
            select(Event).where(Event.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_by_competition(
        self, competition_id: UUID, status: Optional[str] = None, limit: int = 100
    ) -> List[Event]:
        query = select(Event).where(Event.competition_id == competition_id)

        if status:
            query = query.where(Event.status == status)

        query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_upcoming_events(
        self, from_time: datetime, to_time: datetime, limit: int = 100
    ) -> List[Event]:
        result = await self.session.execute(
            select(Event)
            .where(
                and_(
                    Event.commence_time >= from_time,
                    Event.commence_time <= to_time,
                    Event.status == "upcoming"
                )
            )
            .order_by(Event.commence_time)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(self, event_id: UUID, status: str) -> None:
        event = await self.get_by_id(event_id)
        if event:
            event.status = status
            event.updated_at = now_utc()
            await self.session.flush()
            logger.info("event_status_updated", id=str(event_id), status=status)
