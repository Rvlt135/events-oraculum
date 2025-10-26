"""
Adapter for SportsProvider port implementation.
"""
from typing import List, Dict, Any

from app.domain.ports.sports_provider import SportsProvider
from app.adapters.the_odds_api import TheOddsAPIAdapter


class SportsProviderAdapter(SportsProvider):
    """Adapter for TheOddsAPIAdapter to implement SportsProvider port."""

    def __init__(self, api_adapter: TheOddsAPIAdapter):
        self._api_adapter = api_adapter

    async def get_sports(self) -> List[Dict[str, Any]]:
        """Fetch sports data from external provider."""
        return await self._api_adapter.get_sports()

    async def close(self) -> None:
        """Close provider resources."""
        await self._api_adapter.close()
