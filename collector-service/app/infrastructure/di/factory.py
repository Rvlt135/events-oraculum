from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.builders.data_layer.data_layer_builder import DataLayerBuilder
from app.config.settings import settings as _settings, Settings
from app.builders.event_layer.event_layer_builder import EventLayerBuilder
from app.builders.feature_layer.poisson_feature_builder import PoissonFeaturesBuilder
from app.builders.feature_layer.team_features import TeamFeaturesBuilder
from app.builders.feature_layer.match_features import MatchFeaturesBuilder
from app.builders.models_layer.elo_model_builder import EloModelBuilder
from app.builders.models_layer.poisson_model_builder import PoissonModelBuilder
from app.infrastructure.ai.config_loader import get_ai_config_loader
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.cache.catalog.odds import OddsCache
from app.infrastructure.cache.catalog.standings import StandingsFootballCache
from app.infrastructure.cache.events_layer.events_layer_cache import EventsLayerCache
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.cache.models_layer.models_layer_cache import ModelsLayerCache
from app.infrastructure.cache.tasks_cache import TasksCache
from app.infrastructure.di.container import Container
from app.services.event_layer.event_layer_service import EventLayerService
from app.services.models_layer.layer_model_service import LayerModelService
from app.services.odds_service import OddsService
from app.services.data_layer.sports_service import SportsService
from app.services.events_service import EventsService
from app.services.prioritizer_service import PrioritizerService
from app.services.statistics_collect import StatisticsCollectService
from app.services.teams_sync_service import TeamsSyncService
from app.services.feature_layer.team_features import TeamFeaturesService
from app.infrastructure.cache.catalog.events import EventsCache

# if TYPE_CHECKING:
#     from app.services.sports_service import SportsService
#     from app.services.events_service import EventsService
#     from app.services.llm_service import LLMService
#     from app.services.prioritizer_service import PrioritizerService
#     from app.services.teams_sync_service import TeamsSyncService
#     from app.services.feature_layer.team_features import TeamFeaturesService
#
# if TYPE_CHECKING:
#     from app.infrastructure.di.container import Container
#     from app.services.sports_service import SportsService
#     from app.services.events_service import EventsService
#     from app.services.odds_service import OddsService
#     from app.services.feature_layer.team_features import TeamFeaturesService
#     from app.services.models_layer.layer_model_service import LayerModelService


logger = structlog.get_logger()


def get_settings() -> Settings:
    """Get application settings."""
    return _settings


async def get_db_session_from_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session from session factory.
    
    This is a framework-agnostic function that creates and manages
    a database session lifecycle.
    
    Args:
        session_factory: Session factory to create sessions from
    
    Yields:
        AsyncSession instance
    
    Usage:
        async with session_factory() as session:
            # use session
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

def create_sports_service(container: Container) -> "SportsService":
    """
    Factory method for SportsService.

    Returns:
        SportsService instance with dependencies from container
    """
    sports_cache = SportsCache(container.redis_cache)
    competitions_cache = CompetitionsCache(container.redis_cache)
    catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)
    data_builder = DataLayerBuilder(policy_loader=container.policy_loader)
    return SportsService(
        odds_client=container.odds_client,
        session_factory=container.session_factory,
        sports_cache=sports_cache,
        competitions_cache=competitions_cache,
        catalog_cache_helper=catalog_cache_helper,
        policy_loader=container.policy_loader,
        data_builder=data_builder
    )

def create_events_service(container: Container) -> "EventsService":
    """
    Factory method for EventsService.

    Returns:
        EventsService instance with dependencies from container
    """

    sports_cache = SportsCache(container.redis_cache)
    competitions_cache = CompetitionsCache(container.redis_cache)
    events_cache = EventsCache(container.redis_cache)

    return EventsService(
        odds_client=container.odds_client,
        session_factory=container.session_factory,
        sports_cache=sports_cache,
        competitions_cache=competitions_cache,
        events_cache=events_cache,
        policy_loader=container.policy_loader,
    )

def create_prioritizer_service(container: Container) -> "PrioritizerService":
    """
    Factory method for PrioritizerService.

    Returns:
        PrioritizerService instance with dependencies from container

    Raises:
        ValueError: If required prioritizer configuration values are missing
    """
    ai_config = container.ai_config or get_ai_config_loader()
    config = ai_config.load_models_config()
    prioritizer_config = config.get("prioritizer")

    if not prioritizer_config:
        raise ValueError("prioritizer configuration not found in models.yml")

    batch_size = prioritizer_config.get("batch_size")
    if batch_size is None:
        raise ValueError("batch_size not found in prioritizer configuration")

    rate_limit_qps = prioritizer_config.get("rate_limit_qps")
    if rate_limit_qps is None:
        raise ValueError("rate_limit_qps not found in prioritizer configuration")

    max_events = prioritizer_config.get("max_events")
    if max_events is None:
        raise ValueError("max_events not found in prioritizer configuration")

    enabled = prioritizer_config.get("enabled")
    if enabled is None:
        raise ValueError("enabled not found in prioritizer configuration")

    cache_ttl_sec = prioritizer_config.get("cache_ttl_sec")
    if cache_ttl_sec is None:
        raise ValueError("cache_ttl_sec not found in prioritizer configuration")

    events_cache = EventsCache(container.redis_cache)
    tasks_cache = TasksCache(container.redis_broker, rate_limit_qps)

    return PrioritizerService(
        session_factory=container.session_factory,
        redis_cache=container.redis_cache,
        redis_broker=container.redis_broker,
        events_cache=events_cache,
        tasks_cache=tasks_cache,
        batch_size=batch_size,
        max_events=max_events,
        enabled=enabled,
        cache_ttl_sec=cache_ttl_sec,
        ai_client=container.ai_client,
    )

def create_odds_service(container: Container) -> "OddsService":
    """
    Factory method for OddsService.

    Returns:
        OddsService instance with dependencies from container

    Raises:
        ValueError: If required prioritizer configuration values are missing
    """

    events_cache = EventsCache(container.redis_cache)
    odds_cache = OddsCache(container.redis_cache)

    return OddsService(
        odds_client=container.odds_client,
        session_factory=container.session_factory,
        redis_cache=container.redis_cache,
        events_cache=events_cache,
        odds_cache=odds_cache,
        policy_loader=container.policy_loader,
    )

def create_teams_sync_service(container: Container) -> "TeamsSyncService":
    """
    Factory method for TeamsSyncService.

    Returns:
        TeamsSyncService instance with dependencies from container
    """

    competitions_cache = CompetitionsCache(container.redis_cache)
    # events_cache = EventsCache(self.redis_cache)

    return TeamsSyncService(
        api_football_client=container.api_football_client,
        session_factory=container.session_factory,
        policy_loader=container.policy_loader,
        competitions_cache=competitions_cache,
        # events_cache=events_cache
    )

def create_statistics_collect_service(container: Container) -> "StatisticsCollectService":
    """
    Factory method for TeamsSyncService.

    Returns:
        TeamsSyncService instance with dependencies from container
    """

    sports_cache = SportsCache(container.redis_cache)
    competitions_cache = CompetitionsCache(container.redis_cache)
    standings_cache = StandingsFootballCache(container.redis_cache)
    catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)

    return StatisticsCollectService(
        api_football_client=container.api_football_client,
        session_factory=container.session_factory,
        policy_loader=container.policy_loader,
        competitions_cache=competitions_cache,
        standings_football_cache=standings_cache,
        catalog_cache_helper=catalog_cache_helper
    )

def create_team_features_service(container: Container):
    sports_cache = SportsCache(container.redis_cache)
    competitions_cache = CompetitionsCache(container.redis_cache)
    team_features_cache = TeamFeaturesCache(container.redis_cache)
    catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)
    team_feature_builder = TeamFeaturesBuilder()
    match_features_builder = MatchFeaturesBuilder()
    poisson_feature_builder = PoissonFeaturesBuilder()

    return TeamFeaturesService(
        session_factory=container.session_factory,
        team_features_cache=team_features_cache,
        catalog_cache_helper=catalog_cache_helper,
        team_feature_builder=team_feature_builder,
        match_features_builder=match_features_builder,
        poisson_feature_builder=poisson_feature_builder
    )

def create_layer_model_service(container: Container):
    sports_cache = SportsCache(container.redis_cache)
    competitions_cache = CompetitionsCache(container.redis_cache)
    team_features_cache = TeamFeaturesCache(container.redis_cache)
    models_layer_cache = ModelsLayerCache(container.redis_cache)
    catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)
    elo_model_builder = EloModelBuilder()
    poisson_model_builder = PoissonModelBuilder()

    return LayerModelService(
        session_factory=container.session_factory,
        team_features_cache=team_features_cache,
        catalog_cache_helper=catalog_cache_helper,
        elo_model_builder=elo_model_builder,
        poisson_model_builder=poisson_model_builder,
        models_layer_cache=models_layer_cache
    )

def create_event_layer_service(container: Container):
    sports_cache = SportsCache(container.redis_cache)
    competitions_cache = CompetitionsCache(container.redis_cache)
    team_features_cache = TeamFeaturesCache(container.redis_cache)
    event_layer_cache = EventsLayerCache(container.redis_cache)
    catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)
    event_layer_builder = EventLayerBuilder()

    return EventLayerService(
        session_factory=container.session_factory,
        catalog_cache_helper=catalog_cache_helper,
        team_features_cache=team_features_cache,
        event_layer_builder=event_layer_builder,
        event_layer_cache=event_layer_cache,
    )


# TODO: remove legacy di factory duplicate
# def get_sports_service_from_container(container: "Container") -> "SportsService":
#     """
#     Get SportsService from container.
#
#     This is a framework-agnostic function that creates SportsService
#     using the container's factory method.
#
#     Args:
#         container: Container instance with initialized dependencies
#
#     Returns:
#         SportsService instance with dependencies from container
#     """
#     return container.create_sports_service()
#
#
# def get_events_service_from_container(container: "Container") -> "EventsService":
#     """
#     Get EventsService from container.
#
#     This is a framework-agnostic function that creates EventsService
#     using the container's factory method.
#
#     Args:
#         container: Container instance with initialized dependencies
#
#     Returns:
#         EventsService instance with dependencies from container
#     """
#     return container.create_events_service()
#
#
# def get_odds_service_from_container(container: "Container") -> "OddsService":
#     """
#     Get OddsService from container.
#
#     Args:
#         container: Container instance with initialized dependencies
#
#     Returns:
#         OddsService instance with dependencies from container
#     """
#     return container.create_odds_service()
#
# def get_team_features_service_from_container(container: "Container") -> "TeamFeaturesService":
#     """
#     Get OddsService from container.
#
#     Args:
#         container: Container instance with initialized dependencies
#
#     Returns:
#         OddsService instance with dependencies from container
#     """
#     return container.create_team_features_service()
#
#
# def get_layer_model_service_from_container(container: "Container") -> "LayerModelService":
#     """
#     Get LayerModelService from container.
#
#     Args:
#         container: Container instance with initialized dependencies
#
#     Returns:
#         LayerModelService instance with dependencies from container
#     """
#     return container.create_layer_model_service()

# Re-export from sub-modules for convenience
# from app.infrastructure.db.session import make_session_factory
#
# __all__ = [
#     "get_settings",
#     "make_session_factory",
#     "get_db_session_from_factory",
#     "get_sports_service_from_container",
#     "get_events_service_from_container",
#     "get_odds_service_from_container",
#     "get_team_features_service_from_container",
#     "get_layer_model_service_from_container",
# ]
