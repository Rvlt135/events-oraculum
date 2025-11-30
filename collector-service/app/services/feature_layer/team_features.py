"""
Service for building team features
"""
from typing import List
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.builders.feature_layer.match_features import MatchFeaturesBuilder
from app.builders.feature_layer.poisson_feature_builder import PoissonFeaturesBuilder
from app.builders.feature_layer.team_features import TeamFeaturesBuilder
from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import LastFixtureDTO, UpcomingFixtureDTO
from app.domain.entities.statistics.dto.standings_dto import StandingMinimalDTO
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.infrastructure.repositories.feature_layer.match_features import MatchFeaturesRepository
from app.infrastructure.repositories.feature_layer.poisson_feature import PoissonFeatureRepository
from app.infrastructure.repositories.feature_layer.team_features import TeamFeaturesRepository
from app.infrastructure.repositories.fixtures_football import FixturesFootballRepository
from app.infrastructure.repositories.standings import StandingsFootballRepository
from app.infrastructure.repositories.event import EventRepository
from app.infrastructure.db.orm.events import Event

logger = structlog.get_logger()


class TeamFeaturesService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        team_features_cache: TeamFeaturesCache,
        catalog_cache_helper: CatalogCacheHelper,
        team_feature_builder: TeamFeaturesBuilder,
        match_features_builder: MatchFeaturesBuilder,
        poisson_feature_builder: PoissonFeaturesBuilder,
    ):
        self.session_factory = session_factory
        self.team_features_cache = team_features_cache
        self.catalog_cache_helper = catalog_cache_helper
        self.tmf_builder = team_feature_builder
        self.mf_builder = match_features_builder
        self.pf_builder = poisson_feature_builder

    def _extract_team_ids_from_fixtures(self, fixtures: List[UpcomingFixtureDTO]) -> set[UUID]:
        home_ids = {dto.home_team_id for dto in fixtures}
        away_ids = {dto.away_team_id for dto in fixtures}
        team_ids = home_ids.union(away_ids)
        return team_ids

    def _map_events_to_upcoming_fixtures(self, events: list[Event], season: int) -> list[UpcomingFixtureDTO]:
        """Map Event ORM objects to UpcomingFixtureDTO.
        
        Args:
            events: List of Event ORM objects.
            season: Season year.
            
        Returns:
            List of UpcomingFixtureDTO.
        """
        # TODO: refactor Events → Fixtures model
        return [
            UpcomingFixtureDTO(
                event_id=event.id,
                fixture_id=event.id,  # TODO: deprecated, kept for backward compatibility
                match_date=event.commence_time,
                home_team_id=event.home_team_id,
                away_team_id=event.away_team_id,
                competition_id=event.competition_id,
                season=season,
            )
            for event in events
        ]

    async def load_standings_rows(self, competition_id: UUID, season: int) -> List[StandingMinimalDTO]:
        """Load standings rows and convert to minimal DTO for feature generation."""
        async with self.session_factory() as session:
            repo = StandingsFootballRepository(session)
            orm_rows = await repo.get_by_competition(competition_id, season)
            r = self.tmf_builder.build_standings_rows(orm_rows)
            return r

    async def save_team_features(
        self,
        team_features: list[TeamFeaturesDTO],
    ) -> int:
        """Save team features to database and cache."""
        async with self.session_factory() as session:
            repo = TeamFeaturesRepository(session)
            count = await repo.bulk_upsert_team_features(team_features)
            await session.commit()
        
        await self.team_features_cache.save_team_features(team_features)
        return count

    # Match features
    async def load_match_features(self, competition_id: UUID, season: int) -> dict[UUID, list[LastFixtureDTO]]:
        """Load match features from database and cache."""
        async with self.session_factory() as session:
            repo = FixturesFootballRepository(session)
            features = await repo.get_by_competition(competition_id, season)
            build_result = self.mf_builder.load_last_fixtures(features)
            return build_result

    async def save_match_features(self, features: list[MatchFeaturesDTO]) -> int:
        """Save match features to database and cache.
        
        Args:
            features: List of MatchFeaturesDTO records
        """
        async with self.session_factory() as session:
            repo = MatchFeaturesRepository(session)
            count = await repo.bulk_upsert_match_features(features)
            await session.commit()
        
        await self.team_features_cache.save_match_features(features)
        return count

    async def get_events_by_competition(self, competition_id: UUID, season: int) -> tuple[list[UpcomingFixtureDTO], set[UUID]]:
        # TODO: in future change for fixtures repo and fixtures models
        async with self.session_factory() as session:
            events = await EventRepository(session).get_upcoming_by_competition(
                competition_id=competition_id,
                provider="odds_api",
            )
            fixtures = self._map_events_to_upcoming_fixtures(events, season)
            team_ids = self._extract_team_ids_from_fixtures(fixtures)
        return fixtures, team_ids

    # Poisson features
    async def collect_poisson_features_items(self, competition_id: UUID, season: int, fixtures: list[UpcomingFixtureDTO], team_ids: set[UUID]) -> List[PoissonFeaturesDTO]:
        """Collect Poisson features for upcoming fixtures.
        
        Args:
            competition_id: Competition identifier.
            team_ids: Season year.
            season: Season year.
            fixtures: List of UpcomingFixtureDTO.
            team_ids: team id from event and fixtures in future
        Returns:
            List of PoissonFeaturesDTO.
        """
        # TODO: sync Events → fixtures_football_upcoming before Poisson computation
        async with self.session_factory() as session:
            team_features = await TeamFeaturesRepository(session).get_by_team_ids(team_ids, competition_id, season)
            match_features = await MatchFeaturesRepository(session).get_by_team_ids(team_ids, competition_id, season)
            build_result = self.pf_builder.build_for_fixtures(fixtures, team_features, match_features)
            return build_result

    async def save_poisson_features(self, features: list[PoissonFeaturesDTO]) -> int:
        """Save poisson features to database and cache.
        
        Args:
            features: List of PoissonFeaturesDTO records.
            
        Returns:
            Number of processed records.
        """
        logger.debug("save_poisson_features_called", items_count=len(features))
        async with self.session_factory() as session:
            repo = PoissonFeatureRepository(session)
            count = await repo.bulk_upsert_poisson_features(features)
            await session.commit()
        
        logger.debug("save_poisson_features_db_saved", saved_count=count)
        await self.team_features_cache.save_poisson_features(features)
        logger.info("save_poisson_features_completed", saved_count=count)
        return count

