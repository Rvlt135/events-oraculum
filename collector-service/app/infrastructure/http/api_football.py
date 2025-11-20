from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
from httpx import HTTPError

from app.domain.entities.api_football.statistics_dto import TeamStatisticsResponse
from app.infrastructure.http.client import BaseHttpClient
from app.domain.entities.api_football.standings_dto import StandingsResponse, League
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
    async def get_standings(self, league_id: int, season: int, team: Optional[int] = None) -> StandingsResponse:
        params = {"league": league_id, "season": season}
        if team is not None:
            params["team"] = team

        logger.info("fetching_standings", params=params)
        try:
            raw_json = await self.base.get_json("standings", params=params)
        except Exception as exc:
            logger.error("standings_http_failed", error=str(exc))
            raise HTTPError("Failed to fetch standings from external API") from exc

        if not isinstance(raw_json, dict):
            logger.error("standings_unexpected_type", type=type(raw_json).__name__)
            raise ValueError("Standings API must return a dict")

        errors = raw_json.get("errors")
        if (isinstance(errors, dict) and errors) or (isinstance(errors, list) and errors):
            logger.error("standings_api_errors", errors=errors)
            raise ValueError(f"Standings API returned errors: {errors}")

        try:
            response = StandingsResponse.model_validate(raw_json)
        except ValidationError as exc:
            logger.warning("standings_validation_failed", error=str(exc))
            raise ValueError("Unexpected API response structure for standings") from exc

        logger.info("standings_parsed_success")
        return response


    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_team_statistics(self, league_id: int, season: int, team_id: int) -> TeamStatisticsResponse:
        params = {"season": season, "league_id": league_id, "team_id": team_id}
        logger.info("team_statistics_fetching", params=params)
        try:
            raw_json = await self.base.get_json("teams/statistics", params=params)
        except Exception as exc:
            logger.error("team_statistics_http_failed", error=str(exc))
            raise HTTPError("Failed to fetch team_statistics from external API") from exc

        if not isinstance(raw_json, dict):
            logger.error("team_statistics_unexpected_type", type=type(raw_json).__name__)
            raise ValueError("Unexpected response type from team_statistics API")

        errors = raw_json.get("errors")
        if (isinstance(errors, dict) and errors) or (isinstance(errors, list) and errors):
            logger.error("team_statistics_api_errors", errors=errors)
            raise ValueError(f"team_statistics API returned errors: {errors}")

        try:
            response = TeamStatisticsResponse.model_validate(raw_json)
        except ValidationError as exc:
            logger.warning("team_statistics_validation_failed", error=str(exc))
            raise ValueError("Unexpected API response structure for team_statistics") from exc

        logger.info("team_statistics_parsed_success")
        return response
