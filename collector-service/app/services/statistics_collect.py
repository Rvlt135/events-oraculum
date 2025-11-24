from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.infrastructure.http.api_football import APIFootballClient


class StatisticsCollectService:
    def __init__(
        self,
        api_football_client: APIFootballClient,
        session_factory: async_sessionmaker[AsyncSession],
        policy_loader: PolicyLoader,
        competitions_cache: CompetitionsCache,
        # events_cache: EventsCache,
    ):
        self.api_football_client = api_football_client
        self.session_factory = session_factory
        self.policy_loader = policy_loader
        self.competitions_cache = competitions_cache