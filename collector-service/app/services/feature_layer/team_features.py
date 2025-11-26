"""
Service for building team features
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from typing import List
from uuid import UUID

from app.builders.feature_layer.team_features import TeamFeaturesBuilder
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.repositories.standings import StandingsFootballRepository
from app.infrastructure.repositories.feature_layer.team_features import TeamFeaturesRepository
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.statistics.dto.standings_dto import StandingMinimalDTO
from app.infrastructure.cache.catalog.standings import StandingsFootballCache
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.infrastructure.db.orm.standings_football import StandingsFootball

logger = structlog.get_logger()


class TeamFeaturesService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy_loader: PolicyLoader,
        standings_cache: StandingsFootballCache,
        team_features_cache: TeamFeaturesCache,
        catalog_cache_helper: CatalogCacheHelper,
        team_feature_builder: TeamFeaturesBuilder,
    ):
        self.session_factory = session_factory
        self.policy_loader = policy_loader
        self.standings_cache = standings_cache
        self.team_features_cache = team_features_cache
        self.catalog_cache_helper = catalog_cache_helper
        self.tmf_builder = team_feature_builder

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