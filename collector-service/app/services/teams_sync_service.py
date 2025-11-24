"""
Service for syncing teams from API Football.
"""
from typing import Dict, List, Optional
from uuid import UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.api_football.teams_by_league import TeamsResponse
from app.domain.entities.teams import SyncTeamsResult
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.cache.catalog.events import EventsCache
from app.infrastructure.http.api_football import APIFootballClient
from app.infrastructure.repositories.team import TeamRepository
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.config.policy_loader import PolicyLoader, ApiFootballCompetitionDTO
from app.utils.text_utils import create_team_slug

logger = structlog.get_logger()


class TeamsSyncService:
    def __init__(
        self,
        api_football_client: APIFootballClient,
        session_factory: async_sessionmaker[AsyncSession],
        policy_loader: PolicyLoader,
        competitions_cache: CompetitionsCache,
        # events_cache: EventsCache,
    ):
        self.api_football_client = api_football_client
        self.session_factory = session_factory
        self.policy_loader = policy_loader
        self.competitions_cache = competitions_cache

    async def get_competitions_for_sync(self, provider: str, comp_items: dict[str, ApiFootballCompetitionDTO]) -> List[Dict]:
        """
        Get competitions with API Football configuration from policy.

        Returns list of dicts with:
        - competition_slug: str
        - sport_id: UUID
        - league_id: int
        - seasons: list[int]
        """

        competitions_data = []

        async with self.session_factory() as session:
            competitions_repo = CompetitionsRepository(session)

            for competition_slug, comp_config in comp_items.items():
                competition = await competitions_repo.get_by_slug_key(provider, competition_slug)

                if not competition:
                    logger.warning(
                        "competition_not_found_in_db",
                        competition_slug=competition_slug
                    )
                    continue

                if not competition.is_active:
                    logger.debug(
                        "competition_inactive_skipped",
                        competition_slug=competition_slug
                    )
                    continue

                seasons = [comp_config.seasons.current]
                if comp_config.seasons.previous:
                    seasons.append(comp_config.seasons.previous)

                competitions_data.append({
                    "competition_slug": competition_slug,
                    "sport_id": competition.sport_id,
                    "league_id": comp_config.league_id,
                    "seasons": seasons,
                })

            logger.info(
                "competitions_prepared_for_sync",
                total=len(competitions_data),
                provider=provider
            )

            return competitions_data

    async def fetch_teams_by_league(self, league_id: int, season: int) -> Optional[TeamsResponse]:
        logger.info(
            "fetch_teams_started",
            league_id=league_id,
            season=season,
        )

        try:
            teams_response = await self.api_football_client.get_teams_by_league(
                league_id=league_id,
                season=season
            )
        except Exception as e:
            logger.error(
                "teams_teach_failed",
                league_id=league_id,
                season=season,
                error=str(e)
            )
            raise

        if not teams_response.response:
            logger.warning(
                "teams_response_empty",
                league_id=league_id,
                season=season
            )
        return teams_response


    async def sync_teams_for_competition(
        self, sport_id: UUID, league_id: int, season: int,
            teams_response: TeamsResponse
    ) -> SyncTeamsResult:
        """
        Sync teams for a single competition/season from API Football.

        Args:
            sport_id: Sport UUID
            league_id: API Football league ID
            season: Season year
            teams_response: TeamsResponse object from api football

        Returns:
            Dict with created/updated counts
        """
        logger.info(
            "teams_sync_started",
            league_id=league_id,
            season=season,
            sport_id=str(sport_id)
        )

        created = 0
        updated = 0
        collected_slugs: set[str] = set()

        async with self.session_factory() as session:
            team_repo = TeamRepository(session)

            for team_venue in teams_response.response:
                team_data = team_venue.team
                raw_name = team_data.name
                api_football_team_id = team_data.id

                team_slug = create_team_slug(raw_name)
                collected_slugs.add(team_slug)

                existing_team = await team_repo.find_by_slug(sport_id, team_slug)

                if existing_team:
                    updated += 1
                else:
                    created += 1

                await team_repo.upsert_from_api_football(
                    sport_id=sport_id,
                    team_name=raw_name,
                    team_id=api_football_team_id,
                    team_slug=team_slug,
                    external_apif_id=api_football_team_id
                )

            await session.commit()

        logger.info(
            "teams_sync_completed",
            league_id=league_id,
            season=season,
            created=created,
            updated=updated
        )

        return SyncTeamsResult(
            created=created,
            updated=updated,
            team_slugs=list(collected_slugs),
            errors=0
        )
        # return {"created": created, "updated": updated, "team_slugs": list(collected_slugs), "errors": 0}

    async def sync_all_teams(self, provider: str = "odds_api", competitions: list[dict] = None) -> Dict[str, int]:
        """
        Sync teams from API Football for all configured competitions.

        Args:
            provider: Provider name (default: "odds_api")
            competitions: List of competitions to sync
        Returns:
            Summary dict with total created/updated/errors counts
        """
        logger.info("teams_sync_all_started", provider=provider)

        # competitions = await self.get_competitions_for_sync(provider)
        #
        # if not competitions:
        #     logger.warning("no_competitions_for_sync", provider=provider)
        #     return {"created": 0, "updated": 0, "errors": 0}

        total_created = 0
        total_updated = 0
        total_errors = 0

        for comp_data in competitions:
            sport_id = comp_data["sport_id"]
            league_id = comp_data["league_id"]
            seasons = comp_data["seasons"]
            competition_slug = comp_data["competition_slug"]

            for season in seasons:
                logger.info(
                    "syncing_teams_for_competition_season",
                    competition_slug=competition_slug,
                    league_id=league_id,
                    season=season
                )
                try:
                    teams_response = await self.fetch_teams_by_league(league_id=league_id, season=season)
                except Exception as e:
                    logger.error(
                        "teams_fetch_failed_skip_competition_season",
                        competition_slug=competition_slug,
                        league_id=league_id,
                        season=season,
                        error=str(e),
                    )
                    total_errors += 1
                    continue

                result = await self.sync_teams_for_competition(
                    sport_id=sport_id,
                    league_id=league_id,
                    season=season,
                    teams_response=teams_response
                )

                if result.team_slugs:
                    try:
                        await self.competitions_cache.set_competition_team_slugs(
                            competition_slug_key=competition_slug,
                            team_slugs=result.team_slugs,
                            season=season
                        )
                    except Exception as e:
                        logger.error(
                            "teams_cache_failed",
                            competition_slug=competition_slug,
                            error=str(e)
                        )

                total_created += result.created
                total_updated += result.updated
                total_errors += result.errors

        logger.info(
            "teams_sync_all_completed",
            provider=provider,
            total_created=total_created,
            total_updated=total_updated,
            total_errors=total_errors
        )

        return {
            "created": total_created,
            "updated": total_updated,
            "errors": total_errors
        }
