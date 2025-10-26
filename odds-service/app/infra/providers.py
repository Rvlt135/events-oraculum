"""
Unified infrastructure providers for odds-service.

This module provides centralized access to infrastructure resources:
- Database (AsyncEngine, AsyncSession factory)
- Redis client
- TaskIQ broker
- Configuration

All components (main app, scheduler, worker) should import from this module
to avoid duplication of resource initialization.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
import structlog

from app.config.settings import settings
from app.infra.redis_client import RedisManager
from app.domain.services.sports_service import SportsService
from app.infra.adapters.sports_provider_adapter import SportsProviderAdapter
from app.infra.adapters.sports_repository_adapter import SportsRepositoryAdapter
from app.adapters.the_odds_api import TheOddsAPIAdapter
from app.infra.unit_of_work import UnitOfWork

logger = structlog.get_logger()


class InfrastructureProvider:
    """
    Singleton provider for all infrastructure resources.

    Manages lifecycle of:
    - Database engine and session factory
    - Redis client
    - TaskIQ broker (initialized lazily when needed)
    """

    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._redis_manager: Optional[RedisManager] = None
        self._sports_service: Optional[SportsService] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all infrastructure resources."""
        if self._initialized:
            logger.warning("infrastructure_already_initialized")
            return

        # Initialize database
        self._engine = create_async_engine(
            settings.postgres_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        # Initialize Redis
        self._redis_manager = RedisManager()
        await self._redis_manager.initialize()

        # Initialize SportsService
        self._sports_service = self._create_sports_service()

        self._initialized = True
        logger.info("infrastructure_initialized")

    async def dispose(self) -> None:
        """Dispose all infrastructure resources."""
        if not self._initialized:
            return

        if self._redis_manager:
            await self._redis_manager.dispose()

        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

        self._initialized = False
        logger.info("infrastructure_disposed")

    @property
    def engine(self) -> AsyncEngine:
        """Get database engine."""
        if not self._engine:
            raise RuntimeError("Infrastructure not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory."""
        if not self._session_factory:
            raise RuntimeError("Infrastructure not initialized. Call initialize() first.")
        return self._session_factory

    @property
    def redis(self) -> RedisManager:
        """Get Redis manager."""
        if not self._redis_manager:
            raise RuntimeError("Infrastructure not initialized. Call initialize() first.")
        return self._redis_manager

    @property
    def sports_service(self) -> SportsService:
        """Get Sports service."""
        if not self._sports_service:
            raise RuntimeError("Infrastructure not initialized. Call initialize() first.")
        return self._sports_service

    def _create_sports_service(self) -> SportsService:
        """Create SportsService with dependencies."""
        # Create API adapter
        api_adapter = TheOddsAPIAdapter(
            api_key=settings.odds_api_key,
            base_url=settings.odds_api_base_url,
            regions=settings.odds_api_regions,
            markets=settings.odds_api_markets,
        )
        
        # Create provider adapter
        sports_provider = SportsProviderAdapter(api_adapter)
        
        # Note: Repository adapter will be created per-request with session
        # This is handled in the get_sports_service method
        
        return SportsService(
            sports_provider=sports_provider,
            sports_repository=None,  # Will be injected per-request
            unit_of_work=None,  # Will be injected per-request
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency for FastAPI routes to get database session.

        Usage:
            async def handler(session: AsyncSession = Depends(get_db_session)):
                ...
        """
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()


# Global singleton instance
infrastructure = InfrastructureProvider()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session.

    This is the preferred way to get a database session in route handlers.
    """
    async for session in infrastructure.get_session():
        yield session


async def get_sports_service() -> AsyncGenerator[SportsService, None]:
    """
    FastAPI dependency for SportsService with injected dependencies.
    
    Creates a new instance with session-specific dependencies.
    """
    async for session in infrastructure.get_session():
        # Create repository adapter with current session
        sports_repository = SportsRepositoryAdapter(session)
        
        # Create UoW with current session and Redis
        unit_of_work = UnitOfWork(session, infrastructure.redis)
        
        # Create service instance with injected dependencies
        service = SportsService(
            sports_provider=infrastructure.sports_service.sports_provider,
            sports_repository=sports_repository,
            unit_of_work=unit_of_work,
        )
        
        yield service
