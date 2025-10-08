from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.orm_models import League
from .base import BaseRepository

logger = structlog.get_logger()


class LeagueRepository(BaseRepository[League]):
    def __init__(self, session: AsyncSession):
        super().__init__(League, session)

    async def get_or_create(
        self, sport_id: UUID, key: str, name: str, region: str
    ) -> UUID:
        result = await self.session.execute(
            select(League).where(League.key == key)
        )
        league = result.scalar_one_or_none()

        if not league:
            league = League(
                sport_id=sport_id,
                key=key,
                name=name,
                region=region,
                is_active=True
            )
            league = await self.create(league)
            logger.info("league_created", key=key, name=name, id=str(league.id))
        else:
            if league.name != name:
                league.name = name
                await self.session.flush()
                logger.info("league_updated", key=key, new_name=name)

        return league.id

    async def get_by_key(self, key: str) -> Optional[League]:
        result = await self.session.execute(
            select(League).where(League.key == key)
        )
        return result.scalar_one_or_none()

    async def get_active_by_sport(self, sport_id: UUID) -> List[League]:
        result = await self.session.execute(
            select(League)
            .where(League.sport_id == sport_id)
            .where(League.is_active == True)
        )
        return list(result.scalars().all())

    async def deactivate(self, league_id: UUID) -> None:
        league = await self.get_by_id(league_id)
        if league:
            league.is_active = False
            await self.session.flush()
            logger.info("league_deactivated", id=str(league_id))
