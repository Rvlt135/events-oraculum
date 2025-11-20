from typing import Any, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.infrastructure.http.client import BaseHttpClient
from app.infrastructure.providers.odds.schemas import Sport, SportList
from app.utils.mocks.odds_loader import load_mock_odds

logger = structlog.get_logger()


class APIFootballClient:
    def __init__(
            self,
            api_key: str,
            base_url: str,
            use_mock_api_football: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.use_mock_odds = use_mock_api_football

        # Use base client with configuration
        self.base = BaseHttpClient(
            base_url=base_url,
            timeout=30.0,
            limiter=None,  # BaseHttpClient will create default limiter
            default_params={"x-apisports-key": api_key},
        )

    async def close(self) -> None:
        await self.base.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_standings(self,league_id: int, season: int) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_team_statistics(self, league_id: int, season: int, team_id: int) -> List[Dict[str, Any]]:
        raise NotImplementedError()
