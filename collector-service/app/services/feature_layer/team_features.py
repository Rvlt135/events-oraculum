"""
Service for building team features
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.repositories.standings import StandingsFootballRepository
from app.infrastructure.repositories.feature_layer.team_features import TeamFeaturesRepository
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.infrastructure.cache.catalog.standings import StandingsFootballCache
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.config.policy_loader import PolicyLoader

logger = structlog.get_logger()


class TeamFeaturesBuilder:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy_loader: PolicyLoader,
        standings_cache: StandingsFootballCache,
        team_features_cache: TeamFeaturesCache,
    ):
        self.session_factory = session_factory
        self.policy_loader = policy_loader
        self.standings_cache = standings_cache
        self.team_features_cache = team_features_cache

    async def features_from_standings(self, rows) -> list[TeamFeaturesDTO]:
        pass