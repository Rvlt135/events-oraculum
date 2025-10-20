from datetime import datetime
from typing import Any, Dict, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from aiolimiter import AsyncLimiter
import structlog

from app.adapters.dto.odds_api import SportList

logger = structlog.get_logger()


class TheOddsAPIAdapter:
    def __init__(self, api_key: str, base_url: str, regions: List[str], markets: List[str]) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.regions = regions
        self.markets = markets
        self.client = httpx.AsyncClient(timeout=30.0)
        self.limiter = AsyncLimiter(max_rate=10, time_period=60)

    async def close(self) -> None:
        await self.client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_sports(self, active: bool = True) -> List[Dict[str, Any]]:
        async with self.limiter:
            url = f"{self.base_url}/sports"
            params = {"apiKey": self.api_key, "all": active}

            logger.info("fetching_sports", url=url)
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = SportList.model_validate(response.json())
            return data.model_dump(mode="json")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_odds(
        self,
        sport: str,
        regions: List[str] | None = None,
        markets: List[str] | None = None,
    ) -> List[Dict[str, Any]]:
        async with self.limiter:
            url = f"{self.base_url}/sports/{sport}/odds"

            params: Dict[str, Any] = {
                "apiKey": self.api_key,
                "regions": ",".join(regions or self.regions),
                "markets": ",".join(markets or self.markets),
                "dateFormat": "iso",
            }

            logger.info("fetching_odds", sport=sport, regions=regions, markets=markets)
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.info("fetched_odds", sport=sport, count=len(data))
            return data

    async def health_check(self) -> bool:
        try:
            await self.get_sports()
            return True
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return False
