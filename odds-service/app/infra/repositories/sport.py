from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.models.orm.orm_models import Sport
from .base import BaseRepository

logger = structlog.get_logger()


class SportRepository(BaseRepository[Sport]):
    def __init__(self, session: AsyncSession):
        super().__init__(Sport, session)

    async def get_or_create(self, name: str, display_name: str) -> UUID:
        result = await self.session.execute(
            select(Sport).where(Sport.name == name)
        )
        sport = result.scalar_one_or_none()

        if not sport:
            sport = Sport(
                name=name,
                display_name=display_name,
                is_active=True
            )
            sport = await self.create(sport)
            logger.info("sport_created", name=name, id=str(sport.id))

        return sport.id

    async def get_by_name(self, name: str) -> Optional[Sport]:
        result = await self.session.execute(
            select(Sport).where(Sport.name == name)
        )
        return result.scalar_one_or_none()

    async def deactivate(self, sport_id: UUID) -> None:
        sport = await self.get_by_id(sport_id)
        if sport:
            sport.is_active = False
            await self.session.flush()
            logger.info("sport_deactivated", id=str(sport_id))
