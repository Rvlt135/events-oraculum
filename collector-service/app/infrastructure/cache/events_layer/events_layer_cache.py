from typing import Optional
from uuid import UUID

from redis.asyncio import Redis
import structlog

from app.domain.entities.event_layer.dto import EventFeatureBundleDTO

KEY_PREFIX_BUNDLE = "event:bundle"

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
        return f"{KEY_PREFIX_BUNDLE}:{event_id}"

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
        payload = data.model_dump_json()
        
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
                    payload = data.model_dump_json()
                    
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