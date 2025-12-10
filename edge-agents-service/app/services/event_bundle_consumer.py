"""
Service for building team features
"""
from typing import Dict, Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.agents.dto import AgentInputDTO
from app.domain.entities.collector_api.dto import CompetitionReadDTO, UpcomingEventCatalogDTO
from app.domain.entities.collector_api.event_layer_dto import EventFeatureBundleDTO, EventEdgeDTO
from app.infrastructure.cache.catalog.halper import CatalogHalperCache
from app.infrastructure.http.collector_api_client import CollectorApiClient

logger = structlog.get_logger()


class EventBundleConsumer:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        collector_api_client: CollectorApiClient,
        catalog_rdb_halper: CatalogHalperCache,
    ):
        self.session_factory = session_factory
        self.collector_api_client = collector_api_client
        self.catalog_rdb_halper = catalog_rdb_halper

    def to_map_bundles(self, bundles: list[EventFeatureBundleDTO]) -> dict[UUID, EventFeatureBundleDTO]:
        return {b.event_id: b for b in bundles}

    def to_map_edge(self, edge: list[EventEdgeDTO]) -> dict[UUID, EventEdgeDTO]:
        return {b.event_id: b for b in edge}

    def _filter_competitions_by_slug(self, data: Dict[str, Any], slugs: list[str]) -> list[CompetitionReadDTO]:
        slugs_set = set(slugs)
        if not data or "competitions" not in data:
            return []

        competitions_dtos = [CompetitionReadDTO.model_validate(c) for c in data["competitions"]]

        filtered = [c for c in competitions_dtos if c.slug_key in slugs_set]
        return filtered

    async def get_catalog_competitions_by_slug_key(self, category: str, slugs: list[str]) -> list[CompetitionReadDTO]:
        try:
            comp = await self.catalog_rdb_halper.get_catalog_competitions(category)
            result = self._filter_competitions_by_slug(comp, slugs)
            return result
        except Exception as e:
            logger.warning("get_competitions_by_slugs_failed", category=category, error=str(e))
            return []

    async def get_upcoming_events(self, competition_id: UUID, season: int) -> list[UpcomingEventCatalogDTO]:
        try:
            data = await self.collector_api_client.get_upcoming_events(competition_id, season)
            # result = [event.event_id for event in data.events]
            return data.events
        except Exception as e:
            logger.warning("get_upcoming_events_failed", competition_id=competition_id, season=season, error=str(e))
            return []

    async def get_events_bundles_map(self, event_ids: list[UUID]) -> dict[UUID, EventFeatureBundleDTO]:
        try:
            data = await self.collector_api_client.get_events_bundles(event_ids)
            return self.to_map_bundles(data)

        except Exception as e:
            logger.warning("get_events_bundles_failed", event_ids=event_ids, error=str(e))
            return {}

    async def get_events_edge_map(self, event_ids: list[UUID]) -> dict[UUID, EventEdgeDTO]:
        try:
            data = await self.collector_api_client.get_events_edge(event_ids)
            return self.to_map_edge(data)
        except Exception as e:
            logger.warning("get_events_bundles_failed", event_ids=event_ids, error=str(e))
            return {}

    def merge_bundle_edge(self,
                            bundles_map: dict[UUID, EventFeatureBundleDTO],
                            edge_map: dict[UUID, EventEdgeDTO],
                            events: list[UpcomingEventCatalogDTO]
                          ) -> list[AgentInputDTO]:
        result_input = []
        for event in events:
            bundle = bundles_map[event.event_id]
            edge = edge_map[event.event_id]
            ag = AgentInputDTO(
                event_id=event.event_id,
                competition_id=event.competition_id,
                season=event.season,
                match_date=event.date,
                bundle=bundle,
                edge=edge,
            )
            result_input.append(ag)

        return result_input