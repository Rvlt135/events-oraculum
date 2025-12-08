"""
Database session factory.
"""
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create session factory from engine.

    Args:
        engine: Database engine instance

    Returns:
        async_sessionmaker instance
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )