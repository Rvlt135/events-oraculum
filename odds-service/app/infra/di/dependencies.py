from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings as _settings, Settings
from app.infra.db.session import get_db_session


def get_settings() -> Settings:
    return _settings


async def get_task_session() -> AsyncSession:
    """
    Get database session for tasks.
    
    Since TaskIQ doesn't support FastAPI Depends, we create a helper
    that uses the same dependency logic as FastAPI routes.
    """
    async for session in get_db_session():
        return session


# Re-export from sub-modules for convenience
from app.infra.di.session import get_session, get_sessionmaker
from app.infra.di.rdb import get_redis_client
from app.infra.di.services import get_sports_service
from app.infra.di.http import get_odds_api_client
from app.infra.di.lifecycle import initialize as initialize_infrastructure, dispose as dispose_infrastructure

__all__ = [
    "get_settings",
    "get_task_session",
    "get_session",
    "get_sessionmaker",
    "get_redis_client",
    "get_sports_service",
    "get_odds_api_client",
    "initialize_infrastructure",
    "dispose_infrastructure",
]