from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.orm_models import Team
from app.domain.time_utils import now_utc
from .base import BaseRepository

logger = structlog.get_logger()


class TeamRepository(BaseRepository[Team]):
    def __init__(self, session: AsyncSession):
        super().__init__(Team, session)

    async def get_or_create(
        self, name: str, normalized_name: str, sport_id: UUID, external_ids: Dict[str, Any]
    ) -> UUID:
        result = await self.session.execute(
            select(Team).where(Team.normalized_name == normalized_name)
        )
        team = result.scalar_one_or_none()

        if not team:
            team = Team(
                name=name,
                normalized_name=normalized_name,
                sport_id=sport_id,
                external_ids=external_ids
            )
            team = await self.create(team)
            logger.info("team_created", name=name, id=str(team.id))
        else:
            team.name = name
            team.external_ids = external_ids
            team.updated_at = now_utc()
            await self.session.flush()
            logger.debug("team_updated", name=name, id=str(team.id))

        return team.id

    async def get_by_normalized_name(self, normalized_name: str) -> Optional[Team]:
        result = await self.session.execute(
            select(Team).where(Team.normalized_name == normalized_name)
        )
        return result.scalar_one_or_none()

    async def get_by_sport(self, sport_id: UUID) -> List[Team]:
        result = await self.session.execute(
            select(Team).where(Team.sport_id == sport_id)
        )
        return list(result.scalars().all())

    async def search_by_name(self, name_pattern: str, limit: int = 20) -> List[Team]:
        result = await self.session.execute(
            select(Team)
            .where(Team.name.ilike(f"%{name_pattern}%"))
            .limit(limit)
        )
        return list(result.scalars().all())
