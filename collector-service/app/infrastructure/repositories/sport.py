from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.sports import Sport
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class SportRepository(BaseRepository[Sport]):
    def __init__(self, session: AsyncSession):
        super().__init__(Sport, session)

    async def get_or_create(self, category: str, plan_visibility: str, provider: str) -> UUID:
        result = await self.session.execute(
            select(Sport).where(Sport.category == category, Sport.provider == provider)
        )
        sport = result.scalar_one_or_none()

        if not sport:
            sport = Sport(
                category=category,
                provider=provider,
                is_active=True,
                plan_visibility=plan_visibility
            )
            sport = await self.create(sport)
            logger.info("sport_created", category=category, id=str(sport.id), plan_visibility=plan_visibility)
        else:
            if sport.plan_visibility != plan_visibility:
                sport.plan_visibility = plan_visibility
                await self.session.flush()
                logger.info("sport_plan_visibility_updated", category=category, id=str(sport.id), plan_visibility=plan_visibility)

        return sport.id

    async def get_by_category(self, category: str) -> Optional[Sport]:
        result = await self.session.execute(
            select(Sport).where(Sport.category == category)
        )
        return result.scalar_one_or_none()

    async def deactivate(self, sport_id: UUID) -> None:
        sport = await self.get_by_id(sport_id)
        if sport:
            sport.is_active = False
            await self.session.flush()
            logger.info("sport_deactivated", id=str(sport_id))
