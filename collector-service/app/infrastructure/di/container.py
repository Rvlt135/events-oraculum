"""
Dependency injection container and factory functions.
"""
from typing import TYPE_CHECKING
from pathlib import Path
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
import redis.asyncio as redis

from app.infrastructure.db.engine import create_engine
from app.infrastructure.db.session import make_session_factory
from app.infrastructure.http.api_football import APIFootballClient
from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.ai.config_loader import AIConfigLoader, get_ai_config_loader
from app.infrastructure.ai.clients.prioritizer import PrioritizerLLMClient
from app.infrastructure.config.policy_loader import PolicyLoader
from app.services.llm_service import LLMService
from app.config.settings import settings

if TYPE_CHECKING:
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
        self.api_football_client: APIFootballClient | None = None
        self.ai_config: AIConfigLoader | None = None
        self.ai_client: PrioritizerLLMClient | None = None
        self.llm_service: LLMService | None = None
        self.policy_loader: PolicyLoader | None = None
        # self.statistics_collect_service: StatisticsCollectService | None = None

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

