"""
Dependency injection container and factory functions.
"""
from typing import TYPE_CHECKING
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
import redis.asyncio as redis

from app.config.settings import settings
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.db.engine import create_engine
from app.infrastructure.db.session import make_session_factory
from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.ai.config_loader import AIConfigLoader, get_ai_config_loader
from app.infrastructure.ai.clients.prioritizer import PrioritizerLLMClient
from app.services.sports_service import SportsService
from app.services.events_service import EventsService
from app.services.llm_service import LLMService

if TYPE_CHECKING:
    from app.services.sports_service import SportsService
    from app.services.events_service import EventsService
    from app.services.llm_service import LLMService

logger = structlog.get_logger()


class Container:
    """Dependency injection container."""
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.redis_cache: redis.Redis | None = None
        self.redis_broker: redis.Redis | None = None
        self.odds_client: OddsAPIClient | None = None
        self.ai_config: AIConfigLoader | None = None
        self.ai_client: PrioritizerLLMClient | None = None
        self.llm_service: LLMService | None = None
    
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
            catalog_cache_helper=catalog_cache_helper
        )

    def create_events_service(self) -> "EventsService":
        """
        Factory method for EventsService.

        Returns:
            EventsService instance with dependencies from container
        """
        from app.infrastructure.cache.catalog.events import EventsCache
        from app.config.settings import settings

        sports_cache = SportsCache(self.redis_cache)
        competitions_cache = CompetitionsCache(self.redis_cache)
        events_cache = EventsCache(self.redis_cache)

        return EventsService(
            odds_client=self.odds_client,
            session_factory=self.session_factory,
            sports_cache=sports_cache,
            competitions_cache=competitions_cache,
            events_cache=events_cache,
            cache_ttl_sec=settings.catalog_cache_ttl,
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
    )

    # Create AI config loader
    container.ai_config = get_ai_config_loader()

    # Create AI prioritizer client
    container.ai_client = PrioritizerLLMClient(container.ai_config)

    # Create LLM service
    container.llm_service = container.create_llm_service()

    logger.info(
        "container_created",
        has_ai_config=container.ai_config is not None,
        has_ai_client=container.ai_client is not None,
        has_llm_service=container.llm_service is not None
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

