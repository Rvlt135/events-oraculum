"""
Prioritizer service for event prioritization.
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
import redis.asyncio as redis

from app.infrastructure.repositories.event import EventRepository
from app.infrastructure.cache.catalog.events import EventsCache
from app.utils.time_utils import now_utc

logger = structlog.get_logger()


class PrioritizerService:
    """Service for event prioritization data collection and batching."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_cache: redis.Redis,
        events_cache: EventsCache,
        batch_size: int = 50,
        max_events: int = 500,
    ):
        self._session_factory = session_factory
        self._redis_cache = redis_cache
        self._events_cache = events_cache
        self._batch_size = batch_size
        self._max_events = max_events

    async def get_upcoming_events_from_cache(self, provider_key: str) -> List[Dict[str, Any]]:
        """
        Get upcoming events from Redis cache.

        Args:
            provider_key: Provider key for cache lookup

        Returns:
            List of event dicts from cache or empty list
        """
        cache_key = f"catalog:events:{provider_key}:upcoming"

        try:
            cached = await self._events_cache.get_many(cache_key)

            if cached:
                logger.info("events_loaded_from_cache", provider_key=provider_key, count=len(cached))
                return cached

            logger.debug("no_events_in_cache", provider_key=provider_key, cache_key=cache_key)
            return []

        except Exception as e:
            logger.error("cache_read_error", provider_key=provider_key, error=str(e))
            return []

    async def get_upcoming_events_from_db(
        self,
        max_events: int,
        status: str = "planned",
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events from database.

        Args:
            max_events: Maximum number of events to fetch
            status: Event status filter

        Returns:
            List of event dicts from DB
        """
        async with self._session_factory() as session:
            repo = EventRepository(session)

            now = now_utc()

            try:
                events = await repo.get_upcoming_events(
                    from_time=now,
                    to_time=datetime(2099, 12, 31),
                    limit=max_events
                )

                result = []
                for event in events:
                    result.append({
                        "id": str(event.id),
                        "external_id": event.external_id,
                        "sport_id": str(event.sport_id),
                        "competition_id": str(event.competition_id),
                        "home_team_id": str(event.home_team_id),
                        "away_team_id": str(event.away_team_id),
                        "commence_time": event.commence_time.isoformat(),
                        "status": event.status,
                        "provider": event.provider,
                    })

                logger.info(
                    "events_loaded_from_db",
                    count=len(result),
                    status=status,
                    max_events=max_events
                )

                return result

            except Exception as e:
                logger.error("db_read_error", error=str(e), exc_info=True)
                return []

    def deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate events by event_id.

        Args:
            events: List of event dicts

        Returns:
            Deduplicated list
        """
        seen = set()
        result = []

        for event in events:
            event_id = event.get("id")
            if event_id and event_id not in seen:
                seen.add(event_id)
                result.append(event)

        if len(events) != len(result):
            logger.info("events_deduplicated", original=len(events), deduplicated=len(result))

        return result

    def sort_events_by_commence_time(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort events by commence_time ascending.

        Args:
            events: List of event dicts

        Returns:
            Sorted list
        """
        try:
            return sorted(
                events,
                key=lambda e: e.get("commence_time", "9999-12-31T23:59:59")
            )
        except Exception as e:
            logger.warning("sort_error_returning_unsorted", error=str(e))
            return events

    def batch_events(self, events: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Split events into batches.

        Args:
            events: List of event dicts

        Returns:
            List of batches
        """
        if not events:
            return []

        batches = []
        for i in range(0, len(events), self._batch_size):
            batch = events[i:i + self._batch_size]
            batches.append(batch)

        logger.info(
            "events_batched",
            total_events=len(events),
            batch_size=self._batch_size,
            num_batches=len(batches)
        )

        return batches

    async def collect_and_batch_events(
        self,
        provider_key: str = "odds_api",
        max_events: int | None = None,
    ) -> List[List[Dict[str, Any]]]:
        """
        Collect upcoming events and split into batches.

        First tries Redis cache, falls back to DB if cache is empty.
        Deduplicates, sorts by commence_time ASC, and batches.

        Args:
            provider_key: Provider key for cache lookup
            max_events: Maximum events (defaults to service max_events)

        Returns:
            List of batches ready for prioritization
        """
        max_events = max_events or self._max_events

        logger.info(
            "collecting_events_for_prioritization",
            provider_key=provider_key,
            max_events=max_events,
            batch_size=self._batch_size
        )

        events = await self.get_upcoming_events_from_cache(provider_key)

        if not events:
            logger.info("cache_empty_falling_back_to_db")
            events = await self.get_upcoming_events_from_db(max_events)

        if not events:
            logger.warning("no_events_found")
            return []

        events = self.deduplicate_events(events)

        events = self.sort_events_by_commence_time(events)

        batches = self.batch_events(events)

        logger.info(
            "collection_complete",
            total_events=len(events),
            num_batches=len(batches)
        )

        return batches
