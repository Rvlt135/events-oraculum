from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
from httpx import HTTPError
from app.infrastructure.http.client import BaseHttpClient
from app.infrastructure.providers.api_football.schemas import StandingsResponse, League
from app.infrastructure.providers.odds.schemas import Sport, SportList
from app.utils.mocks.odds_loader import load_mock_odds
from pydantic import ValidationError

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(HTTPError))
    async def get_standings(self, league_id: int, season: int, team: Optional[int] = None) -> List[League]:
        params = {"league": league_id, "season": season}
        if team is not None:
            params["team"] = team

        url = self.base.build_url("standings")

        logger.info("fetching_standings", url=url, params=params)
        try:
            raw_json = await self.base.get_json("standings", params=params)
        except Exception as exc:
            logger.error("standings_http_failed", error=str(exc))
            raise HTTPError("Failed to fetch standings from external API") from exc

        if not isinstance(raw_json, dict):
            logger.error("standings_unexpected_type", type=type(raw_json).__name__)
            raise ValueError("Unexpected response type from standings API")

        errors = raw_json.get("errors")
        if (isinstance(errors, dict) and errors) or (isinstance(errors, list) and errors):
            logger.error("standings_api_errors", errors=errors)
            raise ValueError(f"Standings API returned errors: {errors}")

        response_data = raw_json.get("response")
        if not isinstance(response_data, list):
            logger.error("standings_invalid_response", raw=raw_json)
            raise ValueError("Expected 'response' to be a list of leagues")

        payload = {"response": response_data}

        try:
            standings = StandingsResponse.model_validate(payload)
        except ValidationError as exc:
            logger.warning("standings_validation_failed", error=str(exc))
            raise ValueError("Unexpected API response structure for standings") from exc

        logger.info("standings_parsed_success", leagues_count=len(standings.response))
        return standings.response




    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_team_statistics(self, league_id: int, season: int, team_id: int) -> List[Dict[str, Any]]:
        raise NotImplementedError()
