"""
Dependency injection container and factory functions.
"""
from typing import TYPE_CHECKING
from pathlib import Path
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
import redis.asyncio as redis

from app.builders.feature_layer.team_features import TeamFeaturesBuilder
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.cache.catalog.events import EventsCache
from app.infrastructure.cache.catalog.odds import OddsCache
from app.infrastructure.cache.catalog.standings import StandingsFootballCache
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.cache.tasks_cache import TasksCache
from app.infrastructure.db.engine import create_engine
from app.infrastructure.db.session import make_session_factory
from app.infrastructure.http.api_football import APIFootballClient
from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.ai.config_loader import AIConfigLoader, get_ai_config_loader
from app.infrastructure.ai.clients.prioritizer import PrioritizerLLMClient
from app.infrastructure.config.policy_loader import PolicyLoader
from app.services.odds_service import OddsService
from app.services.sports_service import SportsService
from app.services.events_service import EventsService
from app.services.llm_service import LLMService
from app.services.prioritizer_service import PrioritizerService
from app.services.statistics_collect import StatisticsCollectService
from app.services.teams_sync_service import TeamsSyncService
from app.services.feature_layer.team_features import TeamFeaturesService
from app.infrastructure.cache.catalog.events import EventsCache
from app.config.settings import settings

if TYPE_CHECKING:
    from app.services.sports_service import SportsService
    from app.services.events_service import EventsService
    from app.services.llm_service import LLMService
    from app.services.prioritizer_service import PrioritizerService
    from app.services.teams_sync_service import TeamsSyncService
    from app.services.feature_layer.team_features import TeamFeaturesService

logger = structlog.get_logger()


class Container:
    """Dependency injection container."""
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.redis_cache: redis.Redis | None = None
        self.redis_broker: redis.Redis | None = None
        self.odds_client: OddsAPIClient | None = None
        self.api_football_client: APIFootballClient | None = None
        self.ai_config: AIConfigLoader | None = None
        self.ai_client: PrioritizerLLMClient | None = None
        self.llm_service: LLMService | None = None
        self.policy_loader: PolicyLoader | None = None
        self.statistics_collect_service: StatisticsCollectService | None = None
    
    def create_sports_service(self) -> "SportsService":
        """
        Factory method for SportsService.

        Returns:
            SportsService instance with dependencies from container
        """
        sports_cache = SportsCache(self.redis_cache)
        competitions_cache = CompetitionsCache(self.redis_cache)
        catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)
        return SportsService(
            odds_client=self.odds_client,
            session_factory=self.session_factory,
            sports_cache=sports_cache,
            competitions_cache=competitions_cache,
            catalog_cache_helper=catalog_cache_helper,
            policy_loader=self.policy_loader,
        )

    def create_events_service(self) -> "EventsService":
        """
        Factory method for EventsService.

        Returns:
            EventsService instance with dependencies from container
        """

        sports_cache = SportsCache(self.redis_cache)
        competitions_cache = CompetitionsCache(self.redis_cache)
        events_cache = EventsCache(self.redis_cache)

        return EventsService(
            odds_client=self.odds_client,
            session_factory=self.session_factory,
            sports_cache=sports_cache,
            competitions_cache=competitions_cache,
            events_cache=events_cache,
            policy_loader=self.policy_loader,
        )

    def create_llm_service(self) -> "LLMService":
        """
        Factory method for LLMService.

        Returns:
            LLMService instance with AI config from container
        """
        if not self.ai_config:
            logger.warning("ai_config_not_initialized_creating_new")
            self.ai_config = get_ai_config_loader()

        return LLMService(
            ai_config=self.ai_config,
            llm_client=None,
        )

    def create_prioritizer_service(self) -> "PrioritizerService":
        """
        Factory method for PrioritizerService.

        Returns:
            PrioritizerService instance with dependencies from container
        
        Raises:
            ValueError: If required prioritizer configuration values are missing
        """
        ai_config = self.ai_config or get_ai_config_loader()
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
        
        events_cache = EventsCache(self.redis_cache)
        tasks_cache = TasksCache(self.redis_broker, rate_limit_qps)

        return PrioritizerService(
            session_factory=self.session_factory,
            redis_cache=self.redis_cache,
            redis_broker=self.redis_broker,
            events_cache=events_cache,
            tasks_cache=tasks_cache,
            batch_size=batch_size,
            max_events=max_events,
            enabled=enabled,
            cache_ttl_sec=cache_ttl_sec,
            ai_client=self.ai_client,
        )

    def create_odds_service(self) -> "OddsService":
        """
        Factory method for OddsService.

        Returns:
            OddsService instance with dependencies from container

        Raises:
            ValueError: If required prioritizer configuration values are missing
        """

        events_cache = EventsCache(self.redis_cache)
        odds_cache = OddsCache(self.redis_cache)

        return OddsService(
            odds_client=self.odds_client,
            session_factory=self.session_factory,
            redis_cache=self.redis_cache,
            events_cache=events_cache,
            odds_cache=odds_cache,
            policy_loader=self.policy_loader,
        )

    def create_teams_sync_service(self) -> "TeamsSyncService":
        """
        Factory method for TeamsSyncService.

        Returns:
            TeamsSyncService instance with dependencies from container
        """

        competitions_cache = CompetitionsCache(self.redis_cache)
        # events_cache = EventsCache(self.redis_cache)

        return TeamsSyncService(
            api_football_client=self.api_football_client,
            session_factory=self.session_factory,
            policy_loader=self.policy_loader,
            competitions_cache=competitions_cache,
            # events_cache=events_cache
        )

    def create_statistics_collect_service(self) -> "StatisticsCollectService":
        """
        Factory method for TeamsSyncService.

        Returns:
            TeamsSyncService instance with dependencies from container
        """

        sports_cache = SportsCache(self.redis_cache)
        competitions_cache = CompetitionsCache(self.redis_cache)
        standings_cache = StandingsFootballCache(self.redis_cache)
        catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)

        return StatisticsCollectService(
            api_football_client=self.api_football_client,
            session_factory=self.session_factory,
            policy_loader=self.policy_loader,
            competitions_cache=competitions_cache,
            standings_football_cache=standings_cache,
            catalog_cache_helper=catalog_cache_helper
        )

    def create_team_features_service(self):
        sports_cache = SportsCache(self.redis_cache)
        competitions_cache = CompetitionsCache(self.redis_cache)
        team_features_cache = TeamFeaturesCache(self.redis_cache)
        catalog_cache_helper = CatalogCacheHelper(sports_cache, competitions_cache)
        team_feature_builder = TeamFeaturesBuilder()

        return TeamFeaturesService(
            session_factory=self.session_factory,
            policy_loader=self.policy_loader,
            team_features_cache=team_features_cache,
            catalog_cache_helper=catalog_cache_helper,
            team_feature_builder=team_feature_builder,
        )


def create_container() -> Container:
    """
    Create and initialize dependency injection container.
    
    This function creates all infrastructure dependencies:
    - Database engine and session factory
    - Redis client
    - Odds API client
    
    Returns:
        Initialized Container instance
    """
    logger.info("creating_container")
    
    container = Container()
    
    # Create database engine
    container.engine = create_engine(
        settings.postgres_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    
    # Create session factory
    container.session_factory = make_session_factory(container.engine)
    
    # Create Redis client
    container.redis_broker = redis.from_url(settings.redis_broker_url, decode_responses=True)
    container.redis_cache = redis.from_url(settings.redis_cache_url, decode_responses=True)

    # Create Odds API client
    container.odds_client = OddsAPIClient(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        regions=settings.odds_api_regions,
        markets=settings.odds_api_markets,
        use_mock_odds=settings.odds_use_mock,
    )

    container.api_football_client = APIFootballClient(
        api_key=settings.api_football_key,
        base_url=settings.api_football_base_url,
        use_mock_api_football=settings.api_football_use_mock,
    )

    # Create AI config loader with settings
    container.ai_config = AIConfigLoader(settings=settings)

    # Create policy loader and load synchronously (needed for PrioritizerLLMClient)
    policy_path = Path(__file__).parent.parent.parent / "config" / "provider_policy.yml"
    container.policy_loader = PolicyLoader(str(policy_path), load_sync=True)

    # Create AI prioritizer client (policy_loader for business logic, retry from models.yml)
    container.ai_client = PrioritizerLLMClient(container.ai_config, container.policy_loader)

    # Create LLM service
    container.llm_service = container.create_llm_service()

    logger.info(
        "container_created",
        has_ai_config=container.ai_config is not None,
        has_ai_client=container.ai_client is not None,
        has_llm_service=container.llm_service is not None,
        has_policy_loader=container.policy_loader is not None
    )
    return container


async def dispose_container(container: Container) -> None:
    """
    Dispose all resources in container.
    
    Args:
        container: Container instance to dispose
    """
    logger.info("disposing_container")
    
    # Shutdown: close AI client, LLM service, Redis, odds client, and dispose engine
    if container.ai_client:
        await container.ai_client.close()

    if container.llm_service:
        await container.llm_service.close()

    if container.redis_broker:
        await container.redis_broker.close()

    if container.redis_cache:
        await container.redis_cache.close()

    if container.odds_client:
        await container.odds_client.close()

    if container.engine:
        await container.engine.dispose()

    logger.info("container_disposed")

