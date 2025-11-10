from typing import Any, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.infrastructure.http.client import BaseHttpClient
from app.infrastructure.providers.odds.schemas import Sport, SportList

logger = structlog.get_logger()


class OddsAPIClient:
    def __init__(self, api_key: str, base_url: str, regions: List[str], markets: List[str]) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.regions = regions
        self.markets = markets
        
        # Use base client with configuration
        self.base = BaseHttpClient(
            base_url=base_url,
            timeout=30.0,
            limiter=None,  # BaseHttpClient will create default limiter
            default_params={"apiKey": api_key},
        )

    async def close(self) -> None:
        await self.base.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_sports(self, all_sports: bool = False) -> List[Dict[str, Any]]:
        params = {"all": all_sports}
        url = self.base.build_url("sports")
        
        logger.info("fetching_sports", url=url)
        raw_json = await self.base.get_json("sports", params=params)

        # Handle different response structures
        # API might return list directly or wrapped in {"sports": [...]}
        if isinstance(raw_json, list):
            # Response is a list of sports directly
            logger.info("api_returned_list_directly", count=len(raw_json))
            # Validate each sport and return the list
            validated_sports = []
            for sport_data in raw_json:
                try:
                    sport = Sport.model_validate(sport_data)
                    validated_sports.append(sport.model_dump())
                except Exception as e:
                    logger.warning("sport_validation_failed", sport_data=sport_data, error=str(e))
            return validated_sports
        elif isinstance(raw_json, dict) and "sports" in raw_json:
            # Response is wrapped in {"sports": [...]}
            logger.info("api_returned_wrapped_list", count=len(raw_json.get("sports", [])))
            data = SportList.model_validate(raw_json)
            return data.model_dump(mode="json")
        else:
            logger.error("unexpected_response_structure", raw_json=raw_json)
            raise ValueError(f"Unexpected API response structure: {type(raw_json).__name__}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_odds(
        self,
        sport: str,
        regions: List[str] | None = None,
        markets: List[str] | None = None,
        commence_time_from: str | None = None,
        commence_time_to: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Get odds for a sport from The Odds API.

        Args:
            sport: Sport key (e.g., 'soccer_uefa_champs_league')
            regions: List of regions (defaults to instance regions)
            markets: List of markets (defaults to instance markets)
            commence_time_from: ISO-8601 datetime string with Z suffix (optional)
            commence_time_to: ISO-8601 datetime string with Z suffix (optional)

        Returns:
            List of odds data dictionaries
        """
        path = f"sports/{sport}/odds"
        url = self.base.build_url(path)
        
        params: Dict[str, Any] = {
            "regions": ",".join(regions or self.regions),
            "markets": ",".join(markets or self.markets),
            "dateFormat": "iso",
        }

        # Add time window parameters if provided
        if commence_time_from:
            params["commenceTimeFrom"] = commence_time_from
        if commence_time_to:
            params["commenceTimeTo"] = commence_time_to

        logger.info(
            "fetching_odds",
            sport=sport,
            regions=regions,
            markets=markets,
            commence_time_from=commence_time_from,
            commence_time_to=commence_time_to,
            url=url
        )
        data = await self.base.get_json(path, params=params)
        logger.info("fetched_odds", sport=sport, count=len(data))
        return data

    async def health_check(self) -> bool:
        try:
            await self.get_sports()
            return True
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return False
