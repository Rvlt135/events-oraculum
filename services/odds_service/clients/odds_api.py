from datetime import datetime
from typing import Any

import httpx
from shared.config import OddsAPIConfig


class TheOddsAPIClient:
    def __init__(self, config: OddsAPIConfig) -> None:
        self.config = config
        self.base_url = config.odds_api_base_url
        self.api_key = config.odds_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self.client.aclose()

    async def get_sports(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/sports"
        params = {"apiKey": self.api_key}

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_odds(
        self,
        sport: str,
        regions: list[str] | None = None,
        markets: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/sports/{sport}/odds"

        params: dict[str, Any] = {
            "apiKey": self.api_key,
            "regions": ",".join(regions or self.config.odds_api_regions),
            "markets": ",".join(markets or self.config.odds_api_markets),
            "dateFormat": "iso",
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    async def get_event_odds(
        self,
        sport: str,
        event_id: str,
        regions: list[str] | None = None,
        markets: list[str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/sports/{sport}/events/{event_id}/odds"

        params: dict[str, Any] = {
            "apiKey": self.api_key,
            "regions": ",".join(regions or self.config.odds_api_regions),
            "markets": ",".join(markets or self.config.odds_api_markets),
            "dateFormat": "iso",
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    async def health_check(self) -> bool:
        try:
            await self.get_sports()
            return True
        except Exception:
            return False
