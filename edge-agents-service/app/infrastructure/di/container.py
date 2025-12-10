"""
Dependency injection container and factory functions.
"""

import redis.asyncio as redis
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.infrastructure.cache.redis_client import RedisCacheClient
from app.infrastructure.db.engine import create_engine
from app.infrastructure.db.session import make_session_factory
from app.infrastructure.http.collector_api_client import CollectorApiClient

logger = structlog.get_logger()


class Container:
    """Dependency injection container."""

    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.collector_api_client: CollectorApiClient | None = None
        self.redis_cache: redis.Redis | None = None
        self.redis_broker: redis.Redis | None = None
        self.redis_cache_client:  RedisCacheClient | None = None
        self.redis_broker_client: RedisCacheClient | None = None


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

    container.collector_api_client = CollectorApiClient(
        api_key=settings.collector_api_key,
        base_url=settings.collector_api_url,
    )

    # Create session factory
    container.session_factory = make_session_factory(container.engine)

    # Create Redis client
    container.redis_broker = redis.from_url(settings.redis_broker_url, decode_responses=True)
    container.redis_cache = redis.from_url(settings.redis_cache_url, decode_responses=True)

    container.redis_cache_client = RedisCacheClient(raw_redis=container.redis_cache)
    container.redis_broker_client = RedisCacheClient(raw_redis=container.redis_broker)

    return container


async def dispose_container(container: Container) -> None:
    """
    Dispose all resources in container.

    Args:
        container: Container instance to dispose
    """
    logger.info("disposing_container")

    # Shutdown: close AI client, LLM service, Redis, odds client, and dispose engine
    # if container.ai_client:
    #     await container.ai_client.close()
    #
    # if container.llm_service:
    #     await container.llm_service.close()

    if container.redis_broker:
        await container.redis_broker.close()

    if container.redis_cache:
        await container.redis_cache.close()

    if container.engine:
        await container.engine.dispose()

    logger.info("container_disposed")
