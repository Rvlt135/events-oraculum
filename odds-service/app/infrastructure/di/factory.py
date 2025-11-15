"""
Dependency injection functions for creating services and database sessions.

This module provides core DI functions that work with Container directly.
These functions are framework-agnostic and can be used in any context.

For FastAPI-specific wrappers, see app.api.dependencies.
"""
from typing import AsyncGenerator, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings as _settings, Settings

if TYPE_CHECKING:
    from app.infrastructure.di.container import Container
    from app.services.sports_service import SportsService
    from app.services.events_service import EventsService
    from app.services.odds_service import OddsService


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


def get_sports_service_from_container(container: "Container") -> "SportsService":
    """
    Get SportsService from container.

    This is a framework-agnostic function that creates SportsService
    using the container's factory method.

    Args:
        container: Container instance with initialized dependencies

    Returns:
        SportsService instance with dependencies from container
    """
    return container.create_sports_service()


def get_events_service_from_container(container: "Container") -> "EventsService":
    """
    Get EventsService from container.

    This is a framework-agnostic function that creates EventsService
    using the container's factory method.

    Args:
        container: Container instance with initialized dependencies

    Returns:
        EventsService instance with dependencies from container
    """
    return container.create_events_service()


def get_odds_service_from_container(container: "Container") -> "OddsService":
    """
    Get OddsService from container.

    Args:
        container: Container instance with initialized dependencies

    Returns:
        OddsService instance with dependencies from container
    """
    return container.create_odds_service()


# Re-export from sub-modules for convenience
from app.infrastructure.db.session import make_session_factory

__all__ = [
    "get_settings",
    "make_session_factory",
    "get_db_session_from_factory",
    "get_sports_service_from_container",
    "get_events_service_from_container",
    "get_odds_service_from_container",
]
