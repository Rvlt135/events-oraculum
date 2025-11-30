"""
Service for building team features
"""
from typing import List
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.builders.event_layer.event_layer_builder import EventLayerBuilder
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


class EventLayerService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        team_features_cache: TeamFeaturesCache,
        catalog_cache_helper: CatalogCacheHelper,
        event_layer_builder: EventLayerBuilder,
    ):
        self.session_factory = session_factory
        self.catalog_cache_helper = catalog_cache_helper
        self.team_features_cache = team_features_cache

    
    