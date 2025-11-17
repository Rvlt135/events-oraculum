"""
Events cache for storing upcoming events per competition with atomic updates.
"""
from typing import Optional
import structlog
from redis.asyncio import Redis

from app.domain.entities.event import EventDTO
from app.config.settings import settings

logger = structlog.get_logger()


class EventsCache:
    """Cache for upcoming events grouped by competition provider_key."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.key_prefix = "catalog:events"

    def _make_key(self, provider_key: str) -> str:
        """Generate cache key for a competition's upcoming events."""
        return f"{self.key_prefix}:{provider_key}:upcoming"

    def _make_temp_key(self, provider_key: str) -> str:
        """Generate temporary key for atomic swap."""
        return f"{self.key_prefix}:{provider_key}:upcoming:tmp"

    def _make_upcoming_list_key(self, provider: str) -> str:
        """Generate key for competitions with upcoming events index."""
        return f"catalog:competitions:{provider}:with_upcoming"

    async def write_upcoming_atomic(
        self,
        provider_key: str,
        items: list[EventDTO],
        provider: str,
        ttl_sec: Optional[int] = None
    ) -> None:
        """
        Atomically write upcoming events for a competition.

        Uses atomic swap pattern:
        1. Write to temporary key
        2. Rename temporary key to final key
        3. Set TTL if provided (defaults to cache_ttl_events_upcoming_sec from settings)
        4. Update competitions with upcoming index

        TODO: In future, TTL for upcoming events could be made dependent on max(commence_time)
        in batch, rather than a fixed number - separate task.

        Args:
            provider_key: Competition provider_key
            items: List of EventDTO objects (upcoming events only)
            provider: Competition provider service
            ttl_sec: Optional TTL in seconds (defaults to settings.cache_ttl_events_upcoming_sec)
        """
        if ttl_sec is None:
            ttl_sec = settings.cache_ttl_events_upcoming_sec

        temp_key = self._make_temp_key(provider_key)
        final_key = self._make_key(provider_key)
        list_key = self._make_upcoming_list_key(provider)

        try:
            pipe = self.redis.pipeline()

            if not items:
                # Clear cache and remove from index
                await pipe.delete(final_key)
                await pipe.srem(list_key, provider_key)
                await pipe.execute()
                logger.debug(
                    "cleared_empty_events_cache",
                    provider=provider,
                    provider_key=provider_key
                )
                return

            # Write events to cache and add to index
            await pipe.delete(temp_key)
            for event in items:
                event_data = event.model_dump_json()
                await pipe.rpush(temp_key, event_data)
            await pipe.rename(temp_key, final_key)
            if ttl_sec:
                await pipe.expire(final_key, ttl_sec)
            await pipe.sadd(list_key, provider_key)
            await pipe.execute()

            logger.info(
                "events_cache_updated_atomic",
                provider=provider,
                provider_key=provider_key,
                count=len(items),
                ttl_sec=ttl_sec
            )

        except Exception as e:
            logger.error(
                "events_cache_update_failed",
                provider=provider,
                provider_key=provider_key,
                error=str(e),
                exc_info=True
            )
            # Cleanup temp key on error
            try:
                await self.redis.delete(temp_key)
            except Exception:
                pass

    async def get_upcoming(self, provider_key: str) -> list[EventDTO]:
        """
        Get upcoming events for a competition from cache.

        Args:
            provider_key: Competition provider_key

        Returns:
            List of EventDTO objects
        """
        final_key = self._make_key(provider_key)

        try:
            # Get all events from list
            raw_events = await self.redis.lrange(final_key, 0, -1)

            events = []
            for raw_event in raw_events:
                try:
                    event = EventDTO.model_validate_json(raw_event)
                    events.append(event)
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_cached_event",
                        provider_key=provider_key,
                        error=str(e)
                    )

            logger.debug(
                "events_cache_retrieved",
                provider_key=provider_key,
                count=len(events)
            )
            return events

        except Exception as e:
            logger.error(
                "events_cache_retrieval_failed",
                provider_key=provider_key,
                error=str(e)
            )
            return []

    async def read_upcoming(self, provider_key: str) -> list[EventDTO]:
        """
        Read upcoming events for a competition from cache.

        This method is an alias for get_upcoming() to match the service layer interface.

        Args:
            provider_key: Competition provider_key

        Returns:
            List of EventDTO objects
        """
        return await self.get_upcoming(provider_key)

    async def get_many(self, cache_key: str) -> list[dict]:
        """
        Get multiple events from cache by key.

        Args:
            cache_key: Full Redis key

        Returns:
            List of event dicts
        """
        try:
            raw_events = await self.redis.lrange(cache_key, 0, -1)

            events = []
            for raw_event in raw_events:
                try:
                    import json
                    event_dict = json.loads(raw_event)
                    events.append(event_dict)
                except Exception as e:
                    logger.warning("failed_to_parse_cached_event", cache_key=cache_key, error=str(e))

            logger.debug("events_cache_get_many", cache_key=cache_key, count=len(events))
            return events

        except Exception as e:
            logger.error("events_cache_get_many_failed", cache_key=cache_key, error=str(e))
            return []

    async def invalidate(self, provider_key: str) -> None:
        """
        Invalidate (delete) events cache for a competition.

        Args:
            provider_key: Competition provider_key
        """
        final_key = self._make_key(provider_key)

        try:
            await self.redis.delete(final_key)
            logger.debug("events_cache_invalidated", provider_key=provider_key)
        except Exception as e:
            logger.error(
                "events_cache_invalidation_failed",
                provider_key=provider_key,
                error=str(e)
            )
