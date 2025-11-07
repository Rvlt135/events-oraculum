"""
DI for external HTTP clients.
"""
from app.infrastructure.http.odds_api import OddsAPIClient
from app.config.settings import settings


def get_odds_api_client() -> OddsAPIClient:
    """
    Get Odds API client factory.
    
    Usage:
        odds_client = get_odds_api_client()
    """
    return OddsAPIClient(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        regions=settings.odds_api_regions,
        markets=settings.odds_api_markets,
    )
