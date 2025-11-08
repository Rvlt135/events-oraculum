"""
Dependency injection container and factory functions.
"""
from typing import TYPE_CHECKING
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
import redis.asyncio as redis

from app.config.settings import settings
from app.infrastructure.cache.sports import SportsCache
from app.infrastructure.cache.competitions import CompetitionsCache
from app.infrastructure.db.engine import create_engine
from app.infrastructure.db.session import make_session_factory
from app.infrastructure.http.odds_api import OddsAPIClient

if TYPE_CHECKING:
    from app.services.sports_service import SportsService

logger = structlog.get_logger()


class Container:
    """Dependency injection container."""
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.redis: redis.Redis | None = None
        self.odds_client: OddsAPIClient | None = None
    
    def create_sports_service(self) -> "SportsService":
        """
        Factory method for SportsService.
        
        Returns:
            SportsService instance with dependencies from container
        """

        
        return SportsService(
            odds_client=self.odds_client,
            session_factory=self.session_factory,
            sports_cache=SportsCache(self.redis),
            competitions_cache=CompetitionsCache(self.redis),
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
    container.redis = redis.from_url(settings.redis_url, decode_responses=True)
    
    # Create Odds API client
    container.odds_client = OddsAPIClient(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        regions=settings.odds_api_regions,
        markets=settings.odds_api_markets,
    )
    
    logger.info("container_created")
    return container


async def dispose_container(container: Container) -> None:
    """
    Dispose all resources in container.
    
    Args:
        container: Container instance to dispose
    """
    logger.info("disposing_container")
    
    # Shutdown: close Redis, close odds client, and dispose engine
    if container.redis:
        await container.redis.close()
    
    if container.odds_client:
        await container.odds_client.close()
    
    if container.engine:
        await container.engine.dispose()
    
    logger.info("container_disposed")

