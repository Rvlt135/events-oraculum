from typing import Dict, Any, List
import structlog
from prometheus_client import Counter, Histogram
import json
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid import UUID

from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.repositories import NormalizedOddsRepository
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.repositories.sport import SportRepository
from app.infrastructure.cache.sports import SportsCache
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