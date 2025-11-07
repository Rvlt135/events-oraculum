"""
DI for domain services.
"""
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.services.sports_service import SportsService
from app.infrastructure.http.odds_api import OddsAPIClient
from app.config.settings import settings
from app.infrastructure.di.session import get_sessionmaker
from app.infrastructure.di.rdb import get_redis_client


async def get_sports_service() -> SportsService:
    """
    Get SportsService with injected dependencies.
    
    Returns a service instance that manages its own session lifecycle.
    The service will create short-lived sessions per method call.
    """
    # Create Odds API client
    odds_client = OddsAPIClient(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        regions=settings.odds_api_regions,
        markets=settings.odds_api_markets,
    )

    return SportsService(
        odds_client=odds_client,
        session_factory=get_sessionmaker(),
        redis_manager=get_redis_client(),
    )
