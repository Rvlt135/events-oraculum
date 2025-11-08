"""
FastAPI dependencies for database sessions and services.
"""
from typing import AsyncGenerator, TYPE_CHECKING
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.sports_service import SportsService
from app.infrastructure.cache.sports import SportsCache

if TYPE_CHECKING:
    from app.infrastructure.di.container import Container


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
    
    Usage:
        async def handler(session: AsyncSession = Depends(get_db_session)):
            ...
    
    Args:
        session_factory: Session factory from container
    
    Yields:
        AsyncSession instance
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sports_service(request: Request) -> SportsService:
    """
    Get SportsService with injected dependencies from container.
    
    Args:
        request: FastAPI request object
    
    Returns:
        SportsService instance with dependencies from container
    """
    container: "Container" = request.app.state.container
    
    return SportsService(
        odds_client=container.odds_client,
        session_factory=container.session_factory,
        sports_cache=SportsCache(container.redis),
    )

