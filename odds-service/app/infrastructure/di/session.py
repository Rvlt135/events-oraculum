"""
DI for database sessions and session factory.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.session import get_db_session


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Get session factory for DI."""
    return get_session_factory()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session (FastAPI compatible).
    
    This function wraps app.infrastructure.db.session.get_db_session()
    to provide a clean interface for dependency injection.
    """
    async for session in get_db_session():
        yield session
