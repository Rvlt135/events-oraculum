from sqlalchemy.ext.asyncio import create_async_engine

from app.config.settings import settings

engine = create_async_engine(
    settings.postgres_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

