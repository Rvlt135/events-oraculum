from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.models.orm.orm_models import Competitions
from .base import BaseRepository

logger = structlog.get_logger()


class CompetitionsRepository(BaseRepository[Competitions]):
    def __init__(self, session: AsyncSession):
        super().__init__(Competitions, session)

    async def get_or_create(
        self, sport_id: UUID, provider_key: str, title: str, description: str = None
    ) -> UUID:
        result = await self.session.execute(
            select(Competitions).where(Competitions.provider_key == provider_key)
        )
        competition = result.scalar_one_or_none()

        if not competition:
            competition = Competitions(
                sport_id=sport_id,
                provider_key=provider_key,
                title=title,
                description=description,
                is_active=True
            )
            competition = await self.create(competition)
            logger.info("competition_created", key=provider_key, title=title, id=str(competition.id))
        else:
            if competition.title != title:
                competition.title = title
                if description:
                    competition.description = description
                await self.session.flush()
                logger.info("competition_updated", key=provider_key, new_title=title)

        return competition.id

    async def get_by_key(self, key: str) -> Optional[Competitions]:
        result = await self.session.execute(
            select(Competitions).where(Competitions.provider_key == key)
        )
        return result.scalar_one_or_none()

    async def get_active_by_sport(self, sport_id: UUID) -> List[Competitions]:
        result = await self.session.execute(
            select(Competitions)
            .where(Competitions.sport_id == sport_id)
            .where(Competitions.is_active == True)
        )
        return list(result.scalars().all())

    async def deactivate(self, competition_id: UUID) -> None:
        competition = await self.get_by_id(competition_id)
        if competition:
            competition.is_active = False
            await self.session.flush()
            logger.info("competition_deactivated", id=str(competition_id))
