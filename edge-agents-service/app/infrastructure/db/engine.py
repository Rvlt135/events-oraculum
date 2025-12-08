"""
Database engine factory.
"""
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(url: str, **kw) -> AsyncEngine:
    """
    Create and return async database engine.

    Args:
        url: Database connection URL
        **kw: Additional keyword arguments for create_async_engine

    Returns:
        AsyncEngine instance
    """
    return create_async_engine(url, **kw)