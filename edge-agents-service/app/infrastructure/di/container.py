"""
Dependency injection container and factory functions.
"""
from typing import Dict

import redis.asyncio as redis
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from app.config.model_loader import ModelRegistry

from app.config.settings import settings
from app.infrastructure.cache.redis_client import RedisCacheClient
from app.infrastructure.db.engine import create_engine
from app.infrastructure.db.session import make_session_factory
from app.infrastructure.http.collector_api_client import CollectorApiClient
from app.llm.base import BaseLLMClient
from app.llm.clients.factory import create_llm_client, create_all_clients
from app.llm.llm_router import LLMRouter
from app.prompts.processor import PromptProcessor

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
        self.model_registry: ModelRegistry | None = None
        self.llm_clients: Dict[str, BaseLLMClient] | None = None
        self.llm_client: BaseLLMClient | None = None
        self.llm_router: LLMRouter | None = None
        self.prompt_processor: PromptProcessor | None = None


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
    # registry = ModelRegistry(settings.models_config_path)
    container.model_registry = ModelRegistry(settings.models_config_full_path)
    container.llm_client = create_llm_client(settings.active_model_name) # Legacy
    container.llm_clients = create_all_clients(container.model_registry) # create_llm_client(settings.active_model_name)
    container.llm_router = LLMRouter(
        clients=container.llm_clients,
        default_model=container.model_registry.default_model_name,
    )
    container.prompt_processor = PromptProcessor(settings.prompts_config_full_path)


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
