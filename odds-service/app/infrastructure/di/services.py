"""
DI for sports services.
"""
from app.services.sports_service import SportsService
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.repositories.sport import SportRepository
from app.infrastructure.сache.redis_client import get_redis
from app.infrastructure.сache.sports import SportsCache
from app.infrastructure.di.http import get_odds_api_client


async def get_sports_service() -> SportsService:
    """
    Get SportsService with injected dependencies.
    
    Returns a service instance that manages its own session lifecycle.
    The service will create short-lived sessions per method call.
    """
    odds_client = get_odds_api_client()
    cache = SportsCache(get_redis())

    return SportsService(
        odds_client=odds_client,
        session_factory=get_session_factory(),
        sports_cache=cache,
    )
