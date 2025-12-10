import json
from uuid import UUID

import structlog
from redis.asyncio import Redis

from app.domain.entities.event_layer.dto import EventFeatureBundleDTO, EventEdgeDTO

KEY_PREFIX_BUNDLE = "event:bundle"
KEY_PREFIX_EDGE = "event:edge"

logger = structlog.get_logger()


class EventsLayerCache:
    """Redis cache layer for event feature bundles."""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    def _key_bundle(self, event_id: UUID) -> str:
        """Generate Redis key for event feature bundle.
        
        Args:
            event_id: Event identifier.
            
        Returns:
            Redis key string.
        """
        return f"{KEY_PREFIX_BUNDLE}:{event_id}" # TODO: need competition_id and season

    def _key_store_edge(self, event_id: UUID) -> str:
        """Generate Redis key for event feature bundle.

        Args:
            event_id: Event identifier.

        Returns:
            Redis key string.
        """
        return f"{KEY_PREFIX_EDGE}:{event_id}" # TODO: need competition_id and season

    def _deserialize_events_bundle(self, raw_value) -> EventFeatureBundleDTO | None:
        """Deserialize raw JSON string to EventFeatureBundleDTO.
        
        Args:
            raw_value: Raw JSON string from cache or None.
            
        Returns:
            EventFeatureBundleDTO if valid, None otherwise.
        """
        if not raw_value:
            return None
        
        try:
            # Deserialize as-is without modification - DTO handles validation
            data = json.loads(raw_value)
            return EventFeatureBundleDTO(**data)
        except Exception:
            return None

    async def set_bundle(
        self,
        event_id: UUID,
        data: EventFeatureBundleDTO,
        ttl_sec: int | None = None,
    ) -> int:
        """Store event feature bundle in Redis cache.
        
        Args:
            event_id: Event identifier.
            data: Event feature bundle DTO to cache.
            ttl_sec: Optional TTL in seconds.
            
        Returns:
            Number of values written (1 on success, 0 on failure).
        """
        logger.debug("set_bundle_called", event_id=str(event_id))
        
        key = self._key_bundle(event_id)
        # Store JSON as-is without modification - cache is dumb storage
        payload = json.dumps(data.model_dump(mode="json", exclude_none=True))
        
        try:
            if ttl_sec is not None:
                await self._r.set(key, payload, ex=ttl_sec)
            else:
                await self._r.set(key, payload)
            
            logger.debug("set_bundle_completed", event_id=str(event_id))
            return 1
        except Exception as e:
            logger.debug("set_bundle_failed", event_id=str(event_id), error=str(e))
            return 0

    async def set_bundles(
        self,
        items: dict[UUID, EventFeatureBundleDTO],
        ttl_sec: int | None = None,
    ) -> int:
        """Store multiple event feature bundles in Redis cache using pipeline.
        
        Args:
            items: Dictionary mapping event_id to EventFeatureBundleDTO.
            ttl_sec: Optional TTL in seconds.
            
        Returns:
            Number of successfully written items.
        """
        if not items:
            return 0
        
        logger.debug("set_bundles_called", count=len(items))
        
        try:
            async with self._r.pipeline() as pipe:
                for event_id, data in items.items():
                    key = self._key_bundle(event_id)
                    # Store JSON as-is without modification - cache is dumb storage
                    payload = json.dumps(data.model_dump(mode="json", exclude_none=True))
                    
                    if ttl_sec is not None:
                        await pipe.set(key, payload, ex=ttl_sec)
                    else:
                        await pipe.set(key, payload)
                
                results = await pipe.execute()
            
            # Count successful writes (True or "OK" responses)
            success_count = sum(1 for result in results if result)
            
            logger.debug("set_bundles_completed", count=success_count, total=len(items))
            return success_count
        except Exception as e:
            logger.debug("set_bundles_failed", error=str(e), total=len(items))
            return 0

    async def get_bundle(self, event_id: UUID) -> EventFeatureBundleDTO | None:
        """Get event feature bundle from cache by event ID.

        Args:
            event_id: Event identifier.

        Returns:
            EventFeatureBundleDTO if found in cache, None otherwise.
        """
        key = self._key_bundle(event_id)
        raw_value = await self._r.get(key)
        return self._deserialize_events_bundle(raw_value)

    async def get_bundles(self, event_ids: list[UUID]) -> dict[UUID, EventFeatureBundleDTO]:
        """Get event feature bundles from cache by event IDs.

        Args:
            event_ids: List of event identifiers.

        Returns:
            Dictionary mapping event_id to EventFeatureBundleDTO (cache hits only).
        """
        if not event_ids:
            return {}

        logger.debug("get_bundles_called", event_ids_count=len(event_ids))

        async with self._r.pipeline() as pipe:
            for event_id in event_ids:
                key = self._key_bundle(event_id)
                await pipe.get(key)
            raw_values: list[bytes | None] = await pipe.execute()

        result: dict[UUID, EventFeatureBundleDTO] = {}
        for event_id, raw_value in zip(event_ids, raw_values):
            dto = self._deserialize_events_bundle(raw_value)
            if dto is not None:
                result[event_id] = dto

        logger.debug("event_bundles_cache_loaded", fetched_count=len(result))
        return result

    async def store_edges(
        self,
        items: dict[UUID, EventEdgeDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Store event edges in Redis cache using pipeline.
        
        Args:
            items: Dictionary mapping event_id to EventEdgeDTO.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of successfully stored edges.
        """
        if not items:
            return 0
        
        logger.debug(
            "store_edges_called",
            count=len(items),
            competition_id=str(competition_id),
            season=season,
        )
        
        try:
            async with self._r.pipeline() as pipe:
                for event_id, dto in items.items():
                    key = self._key_store_edge(event_id)
                    payload = dto.model_dump_json()
                    await pipe.set(key, payload)
                
                results = await pipe.execute()
            
            # Count successful writes (True or "OK" responses)
            count = sum(1 for result in results if result)
            
            logger.debug("event_edges_cache_stored", count=count)
            return count
        except Exception as e:
            logger.debug("store_edges_failed", error=str(e), total=len(items))
            return 0

    def _deserialize_edge(self, raw_value) -> EventEdgeDTO | None:
        """Deserialize raw JSON string to EventEdgeDTO.
        
        Args:
            raw_value: Raw JSON string from cache or None.
            
        Returns:
            EventEdgeDTO if valid, None otherwise.
        """
        if not raw_value:
            return None
        
        try:
            data = json.loads(raw_value)
            return EventEdgeDTO(**data)
        except Exception:
            return None

    async def get_edges(self, event_ids: list[UUID]) -> dict[UUID, EventEdgeDTO]:
        """Get event edges from cache by event IDs.
        
        Args:
            event_ids: List of event identifiers.
            
        Returns:
            Dictionary mapping event_id to EventEdgeDTO (cache hits only).
        """
        if not event_ids:
            return {}

        logger.debug("get_edges_called", event_ids_count=len(event_ids))

        async with self._r.pipeline() as pipe:
            for event_id in event_ids:
                key = self._key_store_edge(event_id)
                await pipe.get(key)
            raw_values: list[bytes | None] = await pipe.execute()

        result: dict[UUID, EventEdgeDTO] = {}
        for event_id, raw_value in zip(event_ids, raw_values):
            dto = self._deserialize_edge(raw_value)
            if dto is not None:
                result[event_id] = dto

        logger.debug("event_edges_cache_loaded", fetched_count=len(result))
        return result

    async def set_edges(
        self,
        items: dict[UUID, EventEdgeDTO],
        ttl_sec: int | None = None,
    ) -> int:
        """Store event edges in Redis cache using pipeline.
        
        Args:
            items: Dictionary mapping event_id to EventEdgeDTO.
            ttl_sec: Optional TTL in seconds.
            
        Returns:
            Number of successfully stored edges.
        """
        if not items:
            return 0
        
        logger.debug("set_edges_called", count=len(items))
        
        try:
            async with self._r.pipeline() as pipe:
                for event_id, dto in items.items():
                    key = self._key_store_edge(event_id)
                    payload = dto.model_dump_json()
                    
                    if ttl_sec is not None:
                        await pipe.set(key, payload, ex=ttl_sec)
                    else:
                        await pipe.set(key, payload)
                
                results = await pipe.execute()
            
            # Count successful writes (True or "OK" responses)
            count = sum(1 for result in results if result)
            
            logger.debug("set_edges_completed", count=count, total=len(items))
            return count
        except Exception as e:
            logger.debug("set_edges_failed", error=str(e), total=len(items))
            return 0