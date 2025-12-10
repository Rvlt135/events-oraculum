from typing import Any, Dict, List, Optional
from uuid import UUID

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
from httpx import HTTPError

from app.domain.entities.collector_api.dto import CompetitionResponse, CompetitionReadDTO, UpcomingEventCatalogResponse, \
    UpcomingEventCatalogDTO
from app.domain.entities.collector_api.event_layer_dto import EventFeatureBundleDTO, EventEdgeDTO
from app.infrastructure.http.client import BaseHttpClient
from pydantic import ValidationError

logger = structlog.get_logger()


class CollectorApiClient:
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
            default_headers={"X-Admin-Token": api_key},
        )

    async def close(self) -> None:
        await self.base.aclose()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=3), retry=retry_if_exception_type(HTTPError))
    async def get_catalog_competitions(self, category: str, plan: str) -> CompetitionResponse:
        params = {"category": category, "plan": plan}

        logger.info("fetching_catalog_competitions", params=params)
        try:
            raw_json = await self.base.get_json("_admin/catalog/competitions", params=params)
        except Exception as exc:
            logger.error("catalog_competitions_http_failed", error=str(exc))
            raise HTTPError("Failed to fetch catalog competitions from external API") from exc

        if not isinstance(raw_json, dict):
            logger.error("catalog_competitions_unexpected_type", type=type(raw_json).__name__)
            raise ValueError("Catalog competitions API must return a dict")

        try:
            response = CompetitionResponse(competitions=[CompetitionReadDTO(**item) for item in raw_json])
        except ValidationError as exc:
            logger.warning("catalog_competitions_validation_failed", error=str(exc))
            raise ValueError("Unexpected API response structure for catalog competitions") from exc

        logger.info("catalog_competitions_parsed_success")
        return response

    async def get_upcoming_events(self, competition_id: UUID, season: int) -> UpcomingEventCatalogResponse:
        params = {"competition_id": competition_id, "season": season}

        logger.info("fetching_upcoming_events", params=params)
        try:
            raw_json = await self.base.get_json("_admin/catalog/events/upcoming", params=params)
        except Exception as exc:
            logger.error("upcoming_events_http_failed", error=str(exc))
            raise HTTPError("Failed to fetch upcoming events from external API") from exc

        if not isinstance(raw_json, dict):
            logger.error("upcoming_events_unexpected_type", type=type(raw_json).__name__)
            raise ValueError("Upcoming events API must return a dict")

        try:
            response = UpcomingEventCatalogResponse(events=[UpcomingEventCatalogDTO(**item) for item in raw_json])
        except ValidationError as exc:
            logger.warning("upcoming_events_validation_failed", error=str(exc))
            raise ValueError("Unexpected API response structure for upcoming events") from exc

        logger.info("upcoming_events_parsed_success")
        return response

    async def get_events_bundles(self, event_ids: list[UUID]) -> list[EventFeatureBundleDTO]:
        params = [("event_ids", str(eid)) for eid in event_ids]

        logger.info("fetching_events_bundles", params=params)
        try:
            raw_json = await self.base.get_json_multi("events/bundles", params=params)
        except Exception as exc:
            logger.error("events_bundles_http_failed", error=str(exc))
            raise HTTPError("Failed to fetch events bundles from external API") from exc

        if not isinstance(raw_json, dict):
            logger.error("events_bundles_unexpected_type", type=type(raw_json).__name__)
            raise ValueError("Events bundles API must return a dict")

        try:
            response = [EventFeatureBundleDTO.model_validate(ev) for ev in raw_json]
        except ValidationError as exc:
            logger.warning("events_bundles_validation_failed", error=str(exc))
            raise ValueError("Unexpected API response structure for events bundles") from exc

        logger.info("events_bundles_parsed_success")
        return response

    async def get_events_edge(self, event_ids: list[UUID]) -> list[EventEdgeDTO]:
        params = [("event_ids", str(eid)) for eid in event_ids]

        logger.info("fetching_events_edge", params=params)
        try:
            raw_json = await self.base.get_json_multi("events/edges", params=params)
        except Exception as exc:
            logger.error("events_edge_http_failed", error=str(exc))
            raise HTTPError("Failed to fetch events edge from external API") from exc

        if not isinstance(raw_json, dict):
            logger.error("events_edge_unexpected_type", type=type(raw_json).__name__)
            raise ValueError("Events edge API must return a dict")

        try:
            response = [EventEdgeDTO.model_validate(ev) for ev in raw_json]
        except ValidationError as exc:
            logger.warning("events_edge_validation_failed", error=str(exc))
            raise ValueError("Unexpected API response structure for events edge") from exc

        logger.info("events_edge_parsed_success")
        return response