from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import json

from app.infrastructure.db.orm.events import Event
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository
from app.domain.entities.participant import EventUpsertDTO, ParticipantItemDTO
from app.infrastructure.db.orm.competition import Competition

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
        provider: str = "odds_api",
    ) -> UUID:
        result = await self.session.execute(
            select(Event).where(
                Event.provider == provider,
                Event.external_id == external_id
            )
        )
        event = result.scalar_one_or_none()

        if not event:
            event = Event(
                provider=provider,
                external_id=external_id,
                sport_id=sport_id,
                competition_id=competition_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                commence_time=commence_time,
                status=status,
                event_metadata=event_metadata
            )
            event = await self.create(event)
            logger.info("event_created", provider=provider, external_id=external_id, id=str(event.id))
        else:
            event.commence_time = commence_time
            event.status = status
            event.event_metadata = event_metadata
            event.updated_at = now_utc()
            await self.session.flush()
            logger.debug("event_updated", provider=provider, external_id=external_id, id=str(event.id))

        return event.id

    async def get_by_external_id(self, external_id: str, provider: str = "odds_api") -> Optional[Event]:
        result = await self.session.execute(
            select(Event).where(
                Event.provider == provider,
                Event.external_id == external_id
            )
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

    async def upsert_event(self, dto: EventUpsertDTO) -> UUID:
        """
        Create or update an event using flexible EventUpsertDTO.

        This method supports:
        - Optional team references (nullable home_team_id/away_team_id)
        - Flexible participant modes (duel, solo, field, unknown)
        - Deferred team normalization via participants list

        Args:
            dto: EventUpsertDTO with all event data

        Returns:
            UUID of created or updated event
        """
        # Parse commence_time if it's a string
        if isinstance(dto.commence_time, str):
            from dateutil import parser
            commence_time = parser.parse(dto.commence_time)
        else:
            commence_time = dto.commence_time

        # Look up existing event by (provider, external_id)
        result = await self.session.execute(
            select(Event).where(
                Event.provider == dto.provider,
                Event.external_id == dto.external_id
            )
        )
        event = result.scalar_one_or_none()

        # Serialize participants to dict for JSONB storage
        # Use mode="json" to convert UUID to string
        participants_data = [p.model_dump(mode="json", exclude_none=True) for p in dto.participants]

        # Serialize metadata using Pydantic's JSON mode (handles UUID/datetime automatically)
        event_metadata = dto.model_dump(mode="json").get("metadata") if dto.metadata else None

        current_time = now_utc()

        if not event:
            # Create new event
            event = Event(
                provider=dto.provider,
                external_id=dto.external_id,
                sport_id=dto.sport_id,
                competition_id=dto.competition_id,
                home_team_id=dto.home_team_id,
                away_team_id=dto.away_team_id,
                home_team_name=dto.home_team_name,
                away_team_name=dto.away_team_name,
                commence_time=commence_time,
                status=dto.status,
                participant_mode=dto.participant_mode,
                participants=participants_data,
                event_metadata=event_metadata,
                ingested_at=current_time,
                last_seen_at=current_time
            )
            event = await self.create(event)
            logger.info(
                "event_created_flexible",
                provider=dto.provider,
                external_id=dto.external_id,
                id=str(event.id),
                participant_mode=dto.participant_mode,
                participants_count=len(dto.participants)
            )
        else:
            # Update existing event - always update these fields
            event.commence_time = commence_time
            event.home_team_name = dto.home_team_name
            event.away_team_name = dto.away_team_name
            event.participant_mode = dto.participant_mode
            event.participants = participants_data
            event.event_metadata = event_metadata
            event.ingested_at = current_time
            event.last_seen_at = current_time

            # Update team IDs if provided (may be None for solo/field events)
            if dto.home_team_id is not None:
                event.home_team_id = dto.home_team_id
            if dto.away_team_id is not None:
                event.away_team_id = dto.away_team_id

            # Status handling: prevent reverting from canceled to planned
            if dto.status != "canceled" and event.status == "canceled":
                logger.warning(
                    "status_revert_prevented",
                    provider=dto.provider,
                    external_id=dto.external_id,
                    current_status=event.status,
                    attempted_status=dto.status
                )
            else:
                event.status = dto.status

            event.updated_at = current_time
            await self.session.flush()
            logger.debug(
                "event_updated_flexible",
                provider=dto.provider,
                external_id=dto.external_id,
                id=str(event.id),
                participant_mode=dto.participant_mode,
                participants_count=len(dto.participants)
            )

        return event.id

    async def get_upcoming_by_competition(
        self, competition_id: UUID, provider: str = "odds_api"
    ) -> List[Event]:
        """
        Get all upcoming events for a competition.

        Args:
            competition_id: Competition UUID
            provider: Provider name

        Returns:
            List of Event ORM objects where commence_time >= now and status = 'upcoming'
        """
        current_time = now_utc()
        result = await self.session.execute(
            select(Event).where(
                Event.competition_id == competition_id,
                Event.provider == provider,
                Event.commence_time >= current_time,
                Event.status == "upcoming"
            ).order_by(Event.commence_time)
        )
        return list(result.scalars().all())

    async def check_competition_active(self, provider_key: str, provider: str) -> Optional[bool]:
        """
        Check if competition is active by querying the database.

        Args:
            provider_key: Competition provider_key (e.g., 'soccer_uefa_champs_league')
            provider: Provider name (e.g., 'odds_api')

        Returns:
            True if active, False if inactive, None if not found
        """
        result = await self.session.execute(
            select(Competition).where(
                Competition.provider == provider,
                Competition.provider_key == provider_key
            )
        )
        competition = result.scalar_one_or_none()

        if not competition:
            return None

        return competition.is_active
