"""
Service for building team features
"""
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.builders.event_layer.event_layer_builder import EventLayerBuilder
from app.domain.entities.event_layer.dto import EventFeatureBundleDTO, EventEdgeDTO
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.events_layer.events_layer_cache import EventsLayerCache
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.repositories.event_layer.event_layer_repo import EventLayerRepository

logger = structlog.get_logger()


class EventLayerService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        team_features_cache: TeamFeaturesCache,
        catalog_cache_helper: CatalogCacheHelper,
        event_layer_builder: EventLayerBuilder,
        event_layer_cache: EventsLayerCache,
    ):
        self.session_factory = session_factory
        self.catalog_cache_helper = catalog_cache_helper
        self.team_features_cache = team_features_cache
        self.el_builder = event_layer_builder
        self.event_layer_cache = event_layer_cache

    async def persist_enriched_events(
        self,
        bundles: list[EventFeatureBundleDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Persist enriched event feature bundles to database and cache.
        
        Args:
            bundles: List of event feature bundle DTOs to persist.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of processed bundles.
        """
        logger.debug(
            "persist_enriched_events_called",
            count=len(bundles),
            competition_id=str(competition_id),
            season=season,
        )
        
        if not bundles:
            return 0
        
        # Build mapping for cache
        items_map: dict[UUID, EventFeatureBundleDTO] = {
            b.event_id: b for b in bundles
        }
        
        # Persist to DB in batch
        async with self.session_factory() as session:
            event_layer_repo = EventLayerRepository(session)
            await event_layer_repo.store_bundles(
                bundles=bundles,
                competition_id=competition_id,
                season=season,
            )
        
        # Persist to cache in batch
        await self.event_layer_cache.set_bundles(
            items=items_map,
            ttl_sec=None,
        )
        
        logger.debug("persist_enriched_events_completed", count=len(bundles))
        
        return len(bundles)

    async def load_enriched_bundles(self, event_ids: list[UUID]) -> dict[UUID, EventFeatureBundleDTO]:
        """Load enriched event feature bundles from cache and database.
        
        Args:
            event_ids: List of event identifiers to load.
            
        Returns:
            Dictionary mapping event_id to EventFeatureBundleDTO.
        """
        if not event_ids:
            return {}
        
        logger.debug("load_enriched_bundles_called", event_ids_count=len(event_ids))
        
        # Load cached bundles
        cached: dict[UUID, EventFeatureBundleDTO] = await self.event_layer_cache.get_bundles(event_ids)
        
        # Determine missing ids
        missing_ids = set(event_ids) - cached.keys()
        
        if not missing_ids:
            logger.debug("load_enriched_bundles_completed", cached_count=len(cached), missing_count=0)
            return cached
        
        logger.debug("load_enriched_bundles_missing", missing_count=len(missing_ids))
        
        # Load missing bundles from repository
        async with self.session_factory() as session:
            repo = EventLayerRepository(session)
            orm_items = await repo.get_bundles(event_ids=list(missing_ids))
        
        # Parse ORM → DTO using builder
        parsed: dict[UUID, EventFeatureBundleDTO] = self.el_builder.parse_bundles(orm_items)
        
        # Return merged result
        result = {**cached, **parsed}
        
        logger.debug(
            "load_enriched_bundles_completed",
            cached_count=len(cached),
            parsed_count=len(parsed),
            total_count=len(result),
        )
        
        return result

    async def save_edge_bundles(
        self,
        edges: dict[UUID, EventEdgeDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Persist event edges to database and cache.
        
        Args:
            edges: Dictionary mapping event_id to EventEdgeDTO.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of saved edges.
        """
        if not edges:
            return 0
        
        logger.debug(
            "save_edge_bundles_called",
            count=len(edges),
            competition_id=str(competition_id),
            season=season,
        )
        
        # Prepare list for repository
        items_list: list[EventEdgeDTO] = list(edges.values())
        
        # Persist to DB (batch insert)
        async with self.session_factory() as session:
            repo = EventLayerRepository(session)
            db_count = await repo.store_edges(
                items=items_list,
                competition_id=competition_id,
                season=season,
            )
        
        # Persist to Cache
        cache_count = await self.event_layer_cache.store_edges(
            items=edges,
            competition_id=competition_id,
            season=season,
        )
        
        logger.debug(
            "save_edge_bundles_completed",
            db_count=db_count,
            cache_count=cache_count,
        )
        
        return db_count

    async def get_bundle(self, event_id: UUID) -> EventFeatureBundleDTO | None:
        """Get single event feature bundle from cache and database.
        
        Args:
            event_id: Event identifier to fetch bundle for.
            
        Returns:
            EventFeatureBundleDTO if found, None otherwise.
        """
        # Try cache first
        cached = await self.event_layer_cache.get_bundles(event_id)
        if cached is not None:
            return cached
        
        # Load from DB
        async with self.session_factory() as session:
            repo = EventLayerRepository(session)
            raw_json = await repo.get_bundle_json(event_id)
        
        if raw_json is None:
            return None
        
        # Build DTO
        bundle = EventFeatureBundleDTO(**raw_json)
        
        # Cache the result
        await self.event_layer_cache.set_bundle(event_id, bundle)
        
        return bundle

    async def get_events_bundles(
        self,
        event_ids: list[UUID],
    ) -> list[EventFeatureBundleDTO]:
        """Get event feature bundles from cache and database.
        
        Args:
            event_ids: List of event identifiers to fetch bundles for.
            
        Returns:
            List of EventFeatureBundleDTO instances, preserving original order.
        """
        if not event_ids:
            return []
        
        # Cache lookup
        cached: dict[UUID, EventFeatureBundleDTO] = await self.event_layer_cache.get_bundles(event_ids)
        missing: list[UUID] = [eid for eid in event_ids if eid not in cached]
        
        logger.debug("cache_hit", count=len(cached))
        logger.debug("cache_miss", count=len(missing))
        
        # If all found in cache, return early
        if not missing:
            return [cached[eid] for eid in event_ids]
        
        # DB lookup for missing
        async with self.session_factory() as session:
            repo = EventLayerRepository(session)
            rows: dict[UUID, dict | None] = await repo.get_bundles_json(missing)
        
        # Convert raw rows to DTO
        loaded: dict[UUID, EventFeatureBundleDTO] = {}
        for eid, raw_json in rows.items():
            if raw_json:
                try:
                    loaded[eid] = EventFeatureBundleDTO(**raw_json)
                except Exception:
                    logger.debug("bundle_parse_failed", event_id=str(eid))
        
        logger.debug("db_fallback", count=len(loaded))
        
        # Cache set
        if loaded:
            await self.event_layer_cache.set_bundles(loaded)
        
        # Merge maps
        merged: dict[UUID, EventFeatureBundleDTO] = {**cached, **loaded}
        
        logger.debug("merged_count", count=len(merged))
        
        # Return ordered list preserving event_ids input
        return [merged[eid] for eid in event_ids if eid in merged]

    async def get_edges(
        self,
        event_ids: list[UUID],
    ) -> dict[UUID, EventEdgeDTO]:
        """Get event edges from cache and database.
        
        Args:
            event_ids: List of event identifiers to fetch edges for.
            
        Returns:
            Dictionary mapping event_id to EventEdgeDTO, preserving original order.
        """
        if not event_ids:
            return {}
        
        # Batch cache read
        cached_map: dict[UUID, EventEdgeDTO] = await self.event_layer_cache.get_edges(event_ids)
        missing_ids: list[UUID] = [eid for eid in event_ids if eid not in cached_map]
        
        logger.debug("cache_hit", count=len(cached_map))
        logger.debug("cache_miss", count=len(missing_ids))
        
        # If all found in cache, return preserving original order
        if not missing_ids:
            return {eid: cached_map[eid] for eid in event_ids}
        
        # DB lookup for missing
        async with self.session_factory() as session:
            repo = EventLayerRepository(session)
            rows: dict[UUID, dict | None] = await repo.get_edges_json(missing_ids)
        
        # Convert raw_json into EventEdgeDTO
        missing_edges_dict: dict[UUID, EventEdgeDTO] = {}
        for eid, raw_json in rows.items():
            if raw_json is not None:
                try:
                    edge = EventEdgeDTO(**raw_json)
                    missing_edges_dict[eid] = edge
                    logger.debug("edge_loaded", event_id=str(eid))
                except Exception:
                    logger.debug("edge_parse_failed", event_id=str(eid))
        
        logger.debug("db_fallback", count=len(missing_edges_dict))
        
        # Batch cache set
        if missing_edges_dict:
            await self.event_layer_cache.set_edges(missing_edges_dict)
        
        # Merge cached_map + missing_edges_dict
        merged: dict[UUID, EventEdgeDTO] = {**cached_map, **missing_edges_dict}
        
        logger.debug("merged_count", count=len(merged))
        
        # Return final dict preserving original event_ids order
        return {eid: merged[eid] for eid in event_ids if eid in merged}
