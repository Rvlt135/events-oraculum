from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.competition import Competition
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class CompetitionsRepository(BaseRepository[Competition]):
    def __init__(self, session: AsyncSession):
        super().__init__(Competition, session)

    async def get_or_create(
        self,
        sport_id: UUID,
        provider_key: str,
        title: str,
        description: str = None,
        plan_visibility: str = "free",
        provider: str = "odds_api"
    ) -> UUID:
        result = await self.session.execute(
            select(Competition).where(
                Competition.provider_key == provider_key,
                Competition.provider == provider
            )
        )
        competition = result.scalar_one_or_none()

        if not competition:
            competition = Competition(
                sport_id=sport_id,
                provider=provider,
                provider_key=provider_key,
                title=title,
                description=description,
                is_active=True,
                plan_visibility=plan_visibility
            )
            competition = await self.create(competition)
            logger.info("competition_created", key=provider_key, title=title, id=str(competition.id), plan_visibility=plan_visibility)
        else:
            updated = False
            if competition.title != title:
                competition.title = title
                updated = True
            if description and competition.description != description:
                competition.description = description
                updated = True
            if competition.plan_visibility != plan_visibility:
                competition.plan_visibility = plan_visibility
                updated = True
                logger.info("competition_plan_visibility_updated", key=provider_key, id=str(competition.id), plan_visibility=plan_visibility)

            if updated:
                await self.session.flush()
                logger.info("competition_updated", key=provider_key, new_title=title)

        return competition.id

    async def get_by_key(self, key: str) -> Optional[Competition]:
        result = await self.session.execute(
            select(Competition).where(Competition.provider_key == key)
        )
        return result.scalar_one_or_none()

    async def get_active_by_sport(self, sport_id: UUID) -> List[Competition]:
        result = await self.session.execute(
            select(Competition)
            .where(Competition.sport_id == sport_id)
            .where(Competition.is_active == True)
        )
        return list(result.scalars().all())

    async def deactivate(self, competition_id: UUID) -> None:
        competition = await self.get_by_id(competition_id)
        if competition:
            competition.is_active = False
            await self.session.flush()
            logger.info("competition_deactivated", id=str(competition_id))
