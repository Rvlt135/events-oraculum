from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.teams import Team
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository
from sqlalchemy.dialects.postgresql import insert
from app.utils.text_utils import create_team_slug, normalize_name
from app.utils.text_utils import normalize_name

logger = structlog.get_logger()


class TeamRepository(BaseRepository[Team]):
    def __init__(self, session: AsyncSession):
        super().__init__(Team, session)

    async def get_or_create(
        self, name: str, normalized_name: str, sport_id: UUID, external_ids: Dict[str, Any],
        external_apif_id: Optional[int] = None
    ) -> UUID:
        result = await self.session.execute(
            select(Team).where(Team.normalized_name == normalized_name)
        )
        team = result.scalar_one_or_none()

        if not team:
            team_slug = create_team_slug(name)
            team = Team(
                name=name,
                normalized_name=normalized_name,
                team_slug=team_slug,
                sport_id=sport_id,
                external_ids=external_ids,
                external_apif_id=external_apif_id
            )
            team = await self.create(team)
            logger.info("team_created", name=name, id=str(team.id))
        else:
            team.name = name
            team.external_ids = external_ids
            if external_apif_id is not None:
                team.external_apif_id = external_apif_id
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
        self, sport_id: UUID, provider: str, normalized: str, raw: str,
        external_apif_id: Optional[int] = None
    ) -> UUID:
        """
        Resolve team by team_slug or create if not exists.

        Finds team by (sport_id, team_slug), creates if not found,
        and ensures external_ids[provider][raw]=true without overwriting other aliases.

        Args:
            sport_id: Sport UUID
            provider: Provider name (e.g., 'odds_api')
            normalized: Team slug (created via create_team_slug)
            raw: Raw team name from provider

        Returns:
            Team UUID
        """
        # Use normalized as team_slug for searching (it's already a slug from create_team_slug)
        team_slug = normalized

        # Try to find existing team by (sport_id, team_slug)
        result = await self.session.execute(
            select(Team).where(
                Team.sport_id == sport_id,
                Team.team_slug == team_slug
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
                team_slug=team_slug,
                provider=provider,
                raw=raw
            )

            return team.id
        else:
            # Team doesn't exist - create new
            external_ids = {provider: {raw: True}}
            normalized_name = normalize_name(raw)

            team = Team(
                name=raw,
                normalized_name=normalized_name,
                team_slug=team_slug,
                sport_id=sport_id,
                external_ids=external_ids,
                external_apif_id=external_apif_id
            )
            self.session.add(team)
            await self.session.flush()

            logger.info(
                "team_created_with_alias",
                team_id=str(team.id),
                name=raw,
                team_slug=team_slug,
                provider=provider
            )

            return team.id

    async def find_by_slug(self, sport_id: UUID, team_slug: str) -> Optional[Team]:
        """
        Find team by sport_id and team_slug.

        Args:
            sport_id: Sport UUID
            team_slug: Team slug to search for

        Returns:
            Team if found, None otherwise
        """
        result = await self.session.execute(
            select(Team).where(
                Team.sport_id == sport_id,
                Team.team_slug == team_slug
            )
        )
        return result.scalar_one_or_none()

    async def get_many_by_api_ids(self, sport_id: UUID, api_team_ids: list[int]) -> dict[int, Team]:
        if not api_team_ids:
            return {}
        
        result = await self.session.execute(
            select(Team).where(
                Team.sport_id == sport_id,
                Team.external_apif_id.in_(api_team_ids)
            )
        )
        teams = result.scalars().all()
        return {team.external_apif_id: team for team in teams if team.external_apif_id is not None}

    async def upsert_from_api_football(
        self, sport_id: UUID, team_name: str, team_id: int, team_slug: str,
        external_apif_id: Optional[int] = None
    ) -> UUID:
        """
        Upsert team from API Football data.

        Searches by (sport_id, team_slug) to find existing team.
        If found, updates external_ids.api_football.team_id.
        If not found, creates new team.

        Args:
            sport_id: Sport UUID
            team_name: Raw team name from API Football
            team_id: API Football team ID
            team_slug: Computed team slug

        Returns:
            Team UUID
        """
        team = await self.find_by_slug(sport_id, team_slug)

        if team:
            current_external_ids = team.external_ids or {}

            if "api_football" not in current_external_ids:
                current_external_ids["api_football"] = {}

            current_external_ids["api_football"]["team_id"] = team_id

            team.external_ids = current_external_ids
            if external_apif_id is not None:
                team.external_apif_id = external_apif_id
            team.updated_at = now_utc()
            await self.session.flush()

            logger.debug(
                "team_upserted_api_football",
                team_id=str(team.id),
                api_football_team_id=team_id,
                team_slug=team_slug,
                action="updated"
            )

            return team.id
        else:

            normalized_name = normalize_name(team_name)
            external_ids = {"api_football": {"team_id": team_id}}

            team = Team(
                name=team_name,
                normalized_name=normalized_name,
                team_slug=team_slug,
                sport_id=sport_id,
                external_ids=external_ids,
                external_apif_id=external_apif_id
            )
            self.session.add(team)
            await self.session.flush()

            logger.info(
                "team_upserted_api_football",
                team_id=str(team.id),
                name=team_name,
                api_football_team_id=team_id,
                team_slug=team_slug,
                action="created"
            )

            return team.id
