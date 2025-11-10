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

from app.infrastructure.di.dependencies import (
    get_db_session_from_factory,
    get_sports_service_from_container,
    get_events_service_from_container,
)

if TYPE_CHECKING:
    from app.services.sports_service import SportsService
    from app.services.events_service import EventsService


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
    return get_sports_service_from_container(container)


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
    return get_events_service_from_container(container)


def get_redis(request: Request) -> Redis:
    """
    Get Redis client from app state container.

    Args:
        request: FastAPI request object

    Returns:
        Redis client instance from container
    """
    return request.app.state.container.redis

