import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.cache.catalog.sports import SportsCache
logger = structlog.get_logger()


class SnapshotService:
    """Service add snapshot to database."""

    def __init__(
        self,
        odds_client: OddsAPIClient,
        session_factory: async_sessionmaker[AsyncSession],
        sports_cache: SportsCache,
    ):
        self._odds_client = odds_client
        self._session_factory = session_factory
        self._cache = sports_cache