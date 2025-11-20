from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.teams import Team
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository
from sqlalchemy.dialects.postgresql import insert

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

    async def resolve_or_create_by_alias(
        self, sport_id: UUID, provider: str, normalized: str, raw: str
    ) -> UUID:
        """
        Resolve team by normalized name or create if not exists.

        Finds team by (sport_id, normalized_name), creates if not found,
        and ensures external_ids[provider][raw]=true without overwriting other aliases.

        Args:
            sport_id: Sport UUID
            provider: Provider name (e.g., 'odds_api')
            normalized: Normalized team name (lower, trimmed, NFC)
            raw: Raw team name from provider

        Returns:
            Team UUID
        """

        # Try to find existing team by (sport_id, normalized_name)
        result = await self.session.execute(
            select(Team).where(
                Team.sport_id == sport_id,
                Team.normalized_name == normalized
            )
        )
        team = result.scalar_one_or_none()

        if team:
            # Team exists - merge alias into external_ids[provider][raw]
            current_external_ids = team.external_ids or {}

            # Ensure provider dict exists
            if provider not in current_external_ids:
                current_external_ids[provider] = {}

            # Add/update alias
            current_external_ids[provider][raw] = True

            team.external_ids = current_external_ids
            team.updated_at = now_utc()
            await self.session.flush()

            logger.debug(
                "team_alias_added",
                team_id=str(team.id),
                normalized=normalized,
                provider=provider,
                raw=raw
            )

            return team.id
        else:
            # Team doesn't exist - create new
            external_ids = {provider: {raw: True}}

            team = Team(
                name=raw,
                normalized_name=normalized,
                sport_id=sport_id,
                external_ids=external_ids,
            )
            self.session.add(team)
            await self.session.flush()

            logger.info(
                "team_created_with_alias",
                team_id=str(team.id),
                name=raw,
                normalized=normalized,
                provider=provider
            )

            return team.id
