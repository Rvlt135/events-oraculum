from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from uuid import UUID
from typing import List
import structlog

from app.domain.entities.api_football.fixtures_dto import FixturesResponse
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.cache.catalog.standings import StandingsFootballCache
from app.infrastructure.config.policy_loader import PolicyLoader, ApiFootballDTO
from app.infrastructure.db.orm.teams import Team
from app.infrastructure.http.api_football import APIFootballClient
from app.infrastructure.repositories.team import TeamRepository
from app.infrastructure.repositories.standings import StandingsFootballRepository
from app.infrastructure.repositories.fixtures_football import FixturesFootballRepository
from app.domain.entities.statistics.dto.standings_dto import StandingPreparedData, StandingRowDTO, EnrichedStandingRowDTO
from app.domain.entities.statistics.dto.fixtures_dto import PreparedFixturesDTO, PreparedFixtureRowDTO, EloFixtureRecordDTO, FixtureHistoryRecordDTO

logger = structlog.get_logger()


class StatisticsCollectService:
    def __init__(
        self,
        api_football_client: APIFootballClient,
        session_factory: async_sessionmaker[AsyncSession],
        policy_loader: PolicyLoader,
        competitions_cache: CompetitionsCache,
        standings_football_cache: StandingsFootballCache,
        catalog_cache_helper: CatalogCacheHelper
    ):
        self.api_football_client = api_football_client
        self.session_factory = session_factory
        self.policy_loader = policy_loader
        self.competitions_cache = competitions_cache
        self.standings_football_cache = standings_football_cache
        self.catalog_cache_helper = catalog_cache_helper

    def _prepare_teams_map_with_team_id(self, teams_map: dict[int, Team]) -> dict[int, UUID]:
        r = {api_id: team.id for api_id, team in teams_map.items()}
        return r

    def _to_cache_items_standings(self, records: List[EnrichedStandingRowDTO]) -> List[dict]:
        """
        Convert EnrichedStandingRowDTO records to lightweight cache structure.

        Args:
            records: List of EnrichedStandingRowDTO records

        Returns:
            List of lightweight dict items
        """
        return [
            {
                "team_id": str(record.team_id),
                "rank": record.rank,
                "points": record.points,
                "goal_diff": record.goal_diff,
                "form": record.form_raw,
            }
            for record in records
        ]

    def _to_cache_items_fixtures(self, records: List[EloFixtureRecordDTO]) -> List[dict]:
        """
        Convert EloFixtureRecordDTO records to lightweight cache structure.

        Args:
            records: List of EloFixtureRecordDTO records

        Returns:
            List of lightweight dict items
        """
        return [
            {
                "team_id": str(record.team_id),
                "opponent_id": str(record.opponent_id),
                "match_date": record.match_date.isoformat(),
                "goals_for": record.goals_for,
                "goals_against": record.goals_against,
                "is_home": record.is_home,
            }
            for record in records
        ]

    def _build_api_ids_home_away(self, prepared: PreparedFixturesDTO) -> list[int]:
        all_api_team_ids = [row.api_home_id for row in prepared.raw_fixtures_rows]
        all_api_team_ids.extend([row.api_away_id for row in prepared.raw_fixtures_rows])
        all_api_team_ids = list(set(all_api_team_ids))

        return all_api_team_ids

    # STANDINGS
    async def fetch_and_prepare_standings(self, league_id: int, season: int) -> StandingPreparedData:
        """
        Fetch standings from API Football and prepare data for processing.
        
        Args:
            league_id: API Football league ID
            season: Season year
            
        Returns:
            StandingPreparedData with api_team_ids and raw_standings_rows
        """
        standings_response = await self.api_football_client.get_standings(league_id, season)
        
        if standings_response.errors or standings_response.results == 0 or not standings_response.response:
            return StandingPreparedData(api_team_ids=[], raw_standings_rows=[])
        
        league_standings = standings_response.response[0].league.standings

        if not league_standings:
            return StandingPreparedData(api_team_ids=[], raw_standings_rows=[])

        flattened_standings = []
        for level in league_standings:
            flattened_standings.extend(level)
        
        api_team_ids_set = set()
        raw_standings_rows = []
        
        for row in flattened_standings:
            api_team_id = row.team.id
            api_team_ids_set.add(api_team_id)
            
            standing_row = StandingRowDTO(
                api_team_id=api_team_id,
                rank=row.rank,
                points=row.points,
                goal_diff=row.goals_diff,
                all_played=row.all.played,
                all_win=row.all.win,
                all_draw=row.all.draw,
                all_lose=row.all.lose,
                all_goals_for=row.all.goals.for_,
                all_goals_against=row.all.goals.against,
                home_played=row.home.played,
                home_win=row.home.win,
                home_draw=row.home.draw,
                home_lose=row.home.lose,
                home_goals_for=row.home.goals.for_,
                home_goals_against=row.home.goals.against,
                away_played=row.away.played,
                away_win=row.away.win,
                away_draw=row.away.draw,
                away_lose=row.away.lose,
                away_goals_for=row.away.goals.for_,
                away_goals_against=row.away.goals.against,
                form_raw=row.form,
                status=row.status,
                update=row.update
            )
            raw_standings_rows.append(standing_row)
        
        return StandingPreparedData(
            api_team_ids=list(api_team_ids_set),
            raw_standings_rows=raw_standings_rows
        )

    async def resolve_teams_for_standings(self, prepared: StandingPreparedData, sport_id: UUID) -> dict[int, UUID]:
        """
        Resolve API Football team IDs to internal team UUIDs.
        
        Args:
            prepared: StandingPreparedData with api_team_ids
            sport_id: Sport UUID
            
        Returns:
            Dict mapping api_team_id to team UUID
        """

        try:
            if not prepared.api_team_ids:
                return {}
            
            async with self.session_factory() as session:
                team_repo = TeamRepository(session)
                teams_map = await team_repo.get_many_by_api_ids(sport_id, prepared.api_team_ids)
                return self._prepare_teams_map_with_team_id(teams_map)
        except Exception:
            return {}

    def build_standing_records(
        self,
        prepared: StandingPreparedData,
        team_map: dict[int, UUID],
        competition_id: UUID,
        season: int
    ) -> List[EnrichedStandingRowDTO]:
        """
        Build StandingsFootball records from prepared data.
        
        Args:
            prepared: StandingPreparedData with raw_standings_rows
            team_map: Dict mapping api_team_id to team UUID
            competition_id: Competition UUID
            season: Season year
            
        Returns:
            List of EnrichedStandingRowDTO records
        """
        records = []
        
        for row in prepared.raw_standings_rows:
            team_id = team_map.get(row.api_team_id)
            if not team_id:
                continue
            
            record = EnrichedStandingRowDTO(
                team_id=team_id,
                competition_id=competition_id,
                season=season,
                rank=row.rank,
                points=row.points,
                goal_diff=row.goal_diff,
                all_played=row.all_played,
                all_win=row.all_win,
                all_draw=row.all_draw,
                all_lose=row.all_lose,
                all_goals_for=row.all_goals_for,
                all_goals_against=row.all_goals_against,
                home_played=row.home_played,
                home_win=row.home_win,
                home_draw=row.home_draw,
                home_lose=row.home_lose,
                home_goals_for=row.home_goals_for,
                home_goals_against=row.home_goals_against,
                away_played=row.away_played,
                away_win=row.away_win,
                away_draw=row.away_draw,
                away_lose=row.away_lose,
                away_goals_for=row.away_goals_for,
                away_goals_against=row.away_goals_against,
                form_raw=row.form_raw,
                status=row.status,
                raw_payload=row.model_dump(mode="json")
            )
            records.append(record)
        
        return records

    async def save_standings(self, records: List[EnrichedStandingRowDTO], league_id: int, season: int) -> int:
        """
        Save standings records to database and cache.
        
        Args:
            records: List of EnrichedStandingRowDTO records
            league_id: API Football league ID
            season: Season year
            
        Returns:
            Number of saved records
        """
        try:
            async with self.session_factory() as session:
                standings_repo = StandingsFootballRepository(session)
                count = await standings_repo.bulk_upsert(records)
                await session.commit()
                
                items = self._to_cache_items_standings(records)
                try:
                    await self.standings_football_cache.save_standings_teams(str(league_id), season, items)
                except Exception as e:
                    logger.error("standings_cache_save_failed", error=str(e), league_id=league_id, season=season)
                
                return count
        except Exception as e:
            logger.error("standings_save_failed", error=str(e), count=len(records))
            return 0

    # FIXTURES
    async def filter_and_prepare_fixtures(self, fixtures_response: FixturesResponse) -> PreparedFixturesDTO:
        """
        Filter fixtures by status and prepare data for processing.

        Args:
            fixtures_response: FixturesResponse with parsed fixture data

        Returns:
            PreparedFixturesDTO with api_team_ids and raw_fixtures_rows
        """
        if fixtures_response.errors or fixtures_response.results == 0 or not fixtures_response.response:
            return PreparedFixturesDTO(api_team_ids=[], raw_fixtures_rows=[])

        api_team_ids_set = set()
        raw_fixtures_rows = []
        accepted_statuses = {"FT", "AET", "PEN"}

        for row in fixtures_response.response:
            status_short = row.fixture.status.short
            if status_short not in accepted_statuses:
                continue

            api_home_id = row.teams.home.id
            api_away_id = row.teams.away.id

            api_team_ids_set.add(api_home_id)
            api_team_ids_set.add(api_away_id)

            compact_raw_payload = {
                "league": {
                    "id": row.league.id,
                    "season": row.league.season,
                    "round": row.league.round
                },
                "teams": {
                    "home": {
                        "id": api_home_id,
                        "winner": row.teams.home.winner
                    },
                    "away": {
                        "id": api_away_id,
                        "winner": row.teams.away.winner
                    }
                },
                "goals": {
                    "home": row.goals.home,
                    "away": row.goals.away
                },
                "score": {
                    "halftime": row.score.halftime.model_dump(mode="json"),
                    "fulltime": row.score.fulltime.model_dump(mode="json")
                }
            }

            fixture_row = PreparedFixtureRowDTO(
                api_fixture_id=row.fixture.id,
                api_home_id=api_home_id,
                api_away_id=api_away_id,
                goals_home=row.goals.home if row.goals.home is not None else 0,
                goals_away=row.goals.away if row.goals.away is not None else 0,
                match_date=row.fixture.date,
                compact_raw_payload=compact_raw_payload
            )
            raw_fixtures_rows.append(fixture_row)

        return PreparedFixturesDTO(
            api_team_ids=list(api_team_ids_set),
            raw_fixtures_rows=raw_fixtures_rows
        )


    async def resolve_teams_for_fixtures(
        self,
        prepared: PreparedFixturesDTO,
        sport_id: UUID
    ) -> dict[int, UUID]:
        """Resolve internal team UUIDs for fixtures based on API-Football team IDs."""
        try:
            all_api_team_ids = self._build_api_ids_home_away(prepared)
            if not all_api_team_ids:
                return {}
            
            async with self.session_factory() as session:
                team_repo = TeamRepository(session)
                teams_map = await team_repo.get_many_by_api_ids(sport_id, all_api_team_ids)
                return self._prepare_teams_map_with_team_id(teams_map)
        except Exception:
            return {}

    def build_fixture_records(
        self,
        prepared: PreparedFixturesDTO,
        team_map: dict[int, UUID],
        competition_id: UUID,
        season: int
    ) -> List[FixtureHistoryRecordDTO]:
        """Build FixtureHistoryRecordDTO list from prepared fixtures and resolved team IDs."""
        records = []
        
        for row in prepared.raw_fixtures_rows:
            home_team_id = team_map.get(row.api_home_id)
            away_team_id = team_map.get(row.api_away_id)
            
            if not home_team_id or not away_team_id:
                continue
            
            home_goals = row.goals_home
            away_goals = row.goals_away
            
            if home_goals > away_goals:
                result = 1
            elif home_goals < away_goals:
                result = -1
            else:
                result = 0
            
            record = FixtureHistoryRecordDTO(
                api_fixture_id=row.api_fixture_id,
                competition_id=competition_id,
                season=season,
                match_date=row.match_date,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_goals=home_goals,
                away_goals=away_goals,
                result=result,
                raw_payload=row.compact_raw_payload
            )
            records.append(record)
        
        return records

    async def save_fixtures(self, records: list[EloFixtureRecordDTO], league_id: int, season: int) -> dict:
        """
        Save fixtures records to database and cache.
        
        Args:
            records: List of EloFixtureRecordDTO records
            league_id: API Football league ID
            season: Season year
            
        Returns:
            Dict with count of saved records: {"saved": count}
        """
        try:
            async with self.session_factory() as session:
                # Initialize repository and perform bulk upsert
                repo = FixturesFootballRepository(session)

                count = await repo.bulk_upsert_fixtures(records)
                await session.commit()
                
                # Write compact Elo-ready structure to Redis
                items = self._to_cache_items_fixtures(records)
                try:
                    await self.standings_football_cache.save_fixtures_items(str(league_id), season, items)
                except Exception as e:
                    logger.error("fixtures_cache_save_failed", error=str(e), league_id=league_id, season=season)
                
                return {"saved": count}
        except Exception as e:
            logger.error("fixtures_save_failed", error=str(e), count=len(records))
            return {"saved": 0}
