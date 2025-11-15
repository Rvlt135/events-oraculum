from typing import Any, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.infrastructure.http.client import BaseHttpClient
from app.infrastructure.providers.odds.schemas import Sport, SportList
from app.utils.mocks.odds_loader import load_mock_odds

logger = structlog.get_logger()


class OddsAPIClient:
    def __init__(
        self, 
        api_key: str, 
        base_url: str, 
        regions: List[str], 
        markets: List[str],
        use_mock_odds: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.regions = regions
        self.markets = markets
        self.use_mock_odds = use_mock_odds
        
        # Use base client with configuration
        self.base = BaseHttpClient(
            base_url=base_url,
            timeout=30.0,
            limiter=None,  # BaseHttpClient will create default limiter
            default_params={"apiKey": api_key},
        )

    async def close(self) -> None:
        await self.base.aclose()

    async def fetch_odds_mock(self) -> List[Dict[str, Any]]:
        """
        Fetch mock odds data from local JSON file.
        
        Returns:
            List of odds data dictionaries from odds_list.json
        """
        return load_mock_odds()

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
    async def fetch_odds(
        self,
        sport: str,
        regions: List[str] | None = None,
        markets: List[str] | None = None,
        commence_time_from: str | None = None,
        commence_time_to: str | None = None,
        bookmakers: List[str] | None = None,
        include_links: bool = False,
        include_sids: bool = False,
        include_bet_limits: bool = False,
        include_rotation_numbers: bool = False,
        date_format: str = "iso",
        odds_format: str = "decimal",
    ) -> List[Dict[str, Any]]:
        """
        Get odds for a sport from The Odds API.

        Args:
            sport: Sport key (e.g., 'soccer_uefa_champs_league')
            regions: List of regions (defaults to instance regions)
            markets: List of markets (defaults to instance markets)
            commence_time_from: ISO-8601 datetime string with Z suffix (optional)
            commence_time_to: ISO-8601 datetime string with Z suffix (optional)
            bookmakers: List of bookmaker keys (optional)
            include_links: Include links in response (default: False)
            include_sids: Include sids in response (default: False)
            include_bet_limits: Include bet limits in response (default: False)
            include_rotation_numbers: Include rotation numbers in response (default: False)
            date_format: Date format (default: "iso")
            odds_format: Odds format (default: "decimal")

        Returns:
            List of odds data dictionaries
        """
        if self.use_mock_odds:
            logger.info("using_mock_odds_data")
            return await self.fetch_odds_mock()
        
        path = f"sports/{sport}/odds"
        url = self.base.build_url(path)
        
        params: Dict[str, Any] = {
            "regions": ",".join(regions or self.regions),
            "markets": ",".join(markets or self.markets),
            "dateFormat": date_format,
            "oddsFormat": odds_format,
        }

        # Add time window parameters if provided
        if commence_time_from:
            params["commenceTimeFrom"] = commence_time_from
        if commence_time_to:
            params["commenceTimeTo"] = commence_time_to

        # Add bookmakers filter if provided
        if bookmakers:
            params["bookmakers"] = ",".join(bookmakers)

        # Add include flags
        if include_links:
            params["includeLinks"] = "true"
        if include_sids:
            params["includeSids"] = "true"
        if include_bet_limits:
            params["includeBetLimits"] = "true"
        if include_rotation_numbers:
            params["includeRotationNumbers"] = "true"

        logger.info(
            "fetching_odds",
            sport=sport,
            regions=regions,
            markets=markets,
            bookmakers=bookmakers,
            commence_time_from=commence_time_from,
            commence_time_to=commence_time_to,
            url=url
        )
        data = await self.base.get_json(path, params=params)
        logger.info("fetched_odds", sport=sport, count=len(data))
        return data

    async def get_events(
        self,
        provider_key: str,
        from_iso: str,
        to_iso: str,
    ) -> list[dict]:
        """
        Get events for a competition from The Odds API without retries.

        Args:
            provider_key: Competition provider key (e.g., 'soccer_uefa_champs_league')
            from_iso: Start time in ISO-8601 format with Z suffix
            to_iso: End time in ISO-8601 format with Z suffix

        Returns:
            List of event dictionaries

        Note:
            This method does NOT implement retries - retry logic should be handled by the caller.
        """
        path = f"sports/{provider_key}/events"
        url = self.base.build_url(path)

        params: Dict[str, Any] = {
            "dateFormat": "iso",
            "commenceTimeFrom": from_iso,
            "commenceTimeTo": to_iso,
        }

        logger.debug(
            "fetching_events",
            provider_key=provider_key,
            from_iso=from_iso,
            to_iso=to_iso,
            url=url
        )

        data = await self.base.get_json(path, params=params)
        logger.debug("fetched_events", provider_key=provider_key, count=len(data))
        return data

    async def health_check(self) -> bool:
        try:
            await self.get_sports()
            return True
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return False
