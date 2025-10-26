from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings as _settings, Settings
from app.infra.providers import get_db_session


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
