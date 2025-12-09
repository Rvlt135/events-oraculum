"""
FastAPI-specific dependency wrappers.

This module provides thin wrappers around framework-agnostic DI functions
from app.infrastructure.di.dependencies. These wrappers adapt the DI functions
to work with FastAPI's dependency injection system.
"""
from typing import AsyncGenerator, TYPE_CHECKING
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from redis.asyncio import Redis

from app.infrastructure.di.factory import (
    get_db_session_from_factory,
    create_sports_service,
    create_events_service,
    create_odds_service, create_event_layer_service,
    # get_layer_model_service_from_container,
    # get_team_features_service_from_container
)
from app.services.event_layer.event_layer_service import EventLayerService

if TYPE_CHECKING:
    from app.services.data_layer.sports_service import SportsService
    from app.services.events_service import EventsService
    from app.services.odds_service import OddsService


def get_sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    """
    Get session factory from app state container.
    
    Args:
        request: FastAPI request object
    
    Returns:
        async_sessionmaker instance from container
    """
    return request.app.state.container.session_factory


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_sessionmaker)
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session.
    
    This is a thin wrapper around get_db_session_from_factory that integrates
    with FastAPI's dependency injection system.
    
    Usage:
        async def handler(session: AsyncSession = Depends(get_db_session)):
            ...
    
    Args:
        session_factory: Session factory from container (injected by FastAPI)
    
    Yields:
        AsyncSession instance
    """
    async for session in get_db_session_from_factory(session_factory):
        yield session


def get_sports_service(request: Request) -> "SportsService":
    """
    Get SportsService with injected dependencies from container.

    This is a thin wrapper around get_sports_service_from_container that
    extracts the container from FastAPI's request object.

    Args:
        request: FastAPI request object

    Returns:
        SportsService instance with dependencies from container
    """
    container = request.app.state.container
    return create_sports_service(container)


def get_events_service(request: Request) -> "EventsService":
    """
    Get EventsService with injected dependencies from container.

    This is a thin wrapper around get_events_service_from_container that
    extracts the container from FastAPI's request object.

    Args:
        request: FastAPI request object

    Returns:
        EventsService instance with dependencies from container
    """
    container = request.app.state.container
    return create_events_service(container)

def get_event_layer_service(request: Request) -> "EventLayerService":
    """
    Get EventLayerService with injected dependencies from container.

    This is a thin wrapper around  that
    extracts the container from FastAPI's request object.

    Args:
        request: FastAPI request object

    Returns:
        EventLayerService instance with dependencies from container
    """
    container = request.app.state.container
    return create_event_layer_service(container)


def get_odds_service(request: Request) -> "OddsService":
    """
    Get OddsService with injected dependencies from container.

    Args:
        request: FastAPI request object

    Returns:
        OddsService instance with dependencies from container
    """
    container = request.app.state.container
    return create_odds_service(container)

def get_redis_cache(request: Request) -> Redis:
    """
    Get Redis cache client from app state container.

    Args:
        request: FastAPI request object

    Returns:
        Redis client instance from container
    """
    return request.app.state.container.redis_cache

