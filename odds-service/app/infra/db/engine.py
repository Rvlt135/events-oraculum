"""
Database engine factory and lifecycle management.
"""
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from app.config.settings import settings

_engine: AsyncEngine | None = None


def create_engine() -> AsyncEngine:
    """Create and return async database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.postgres_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_engine() -> AsyncEngine:
    """Get database engine (create if not exists)."""
    return create_engine()


async def dispose_engine() -> None:
    """Dispose database engine."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
