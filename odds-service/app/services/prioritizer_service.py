"""
Prioritizer service for event prioritization.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import json
import structlog
import asyncio
import secrets
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
import redis.asyncio as redis

from app.infrastructure.cache.tasks_cache import TasksCache
from app.infrastructure.repositories.event import EventRepository
from app.infrastructure.repositories.event_priority import EventPriorityRepository
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.cache.catalog.events import EventsCache
from app.infrastructure.ai.clients.prioritizer import PrioritizerLLMClient
from app.utils.time_utils import now_utc
from app.domain.entities.event import EventDTO

logger = structlog.get_logger()


class PrioritizerService:
    """Service for event prioritization data collection and batching."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_cache: redis.Redis,
        redis_broker: redis.Redis,
        events_cache: EventsCache,
        tasks_cache: TasksCache,
        batch_size: int,
        max_events: int,
        enabled: bool,
        cache_ttl_sec: int,
        ai_client: Optional[PrioritizerLLMClient] = None,
    ):
        self._session_factory = session_factory
        self._redis_cache = redis_cache
        self._redis_broker = redis_broker
        self._events_cache = events_cache
        self.tasks_cache = tasks_cache
        self._ai_client = ai_client
        self._batch_size = batch_size
        self._max_events = max_events
        self._enabled = enabled
        self._cache_ttl_sec = cache_ttl_sec
        # self._rate_limit_qps = rate_limit_qps # TODO: delete after tests

    async def get_upcoming_events_from_cache(self, provider_key: str) -> List[EventDTO]:
        """
        Get upcoming events from Redis cache.

        Args:
            provider_key: Provider key for cache lookup

        Returns:
            List of EventDTO from cache or empty list
        """
        try:
            cached = await self._events_cache.get_upcoming(provider_key)

            if cached:
                logger.info("events_loaded_from_cache", provider_key=provider_key, count=len(cached))
                return cached

            logger.debug("no_events_in_cache", provider_key=provider_key)
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

    async def get_upcoming_events_for_provider_key(
        self,
        provider_key: str,
        provider: str = "odds_api",
    ) -> List[EventDTO]:
        """
        Get upcoming events for a provider_key (cache-first, then DB fallback).

        Args:
            provider_key: Competition provider_key
            provider: Provider name

        Returns:
            List of EventDTO (empty if none found)
        """
        # Try cache first
        events = await self.get_upcoming_events_from_cache(provider_key)

        if events:
            return events

        # Fallback to DB
        async with self._session_factory() as session:
            comp_repo = CompetitionsRepository(session)
            event_repo = EventRepository(session)

            try:
                competition = await comp_repo.get_by_provider_key(
                    provider=provider,
                    provider_key=provider_key
                )

                if not competition:
                    logger.debug("competition_not_found", provider_key=provider_key, provider=provider)
                    return []

                events_orm = await event_repo.get_upcoming_by_competition(
                    competition_id=competition.id,
                    provider=provider
                )

                result = []
                for event in events_orm:
                    dto = EventDTO(
                        id=event.id,
                        provider=event.provider,
                        external_id=event.external_id,
                        sport_id=event.sport_id,
                        competition_id=event.competition_id,
                        home_team_id=event.home_team_id,
                        away_team_id=event.away_team_id,
                        home_team_name=event.home_team_name,
                        away_team_name=event.away_team_name,
                        commence_time=event.commence_time,
                        status=event.status,
                        participant_mode=event.participant_mode,
                        participants=event.participants or [],
                        metadata=event.event_metadata or {},
                        created_at=event.created_at,
                        updated_at=event.updated_at,
                        ingested_at=event.ingested_at,
                        last_seen_at=event.last_seen_at
                    )
                    result.append(dto)

                logger.info(
                    "events_loaded_from_db_for_provider_key",
                    provider_key=provider_key,
                    count=len(result)
                )

                return result

            except Exception as e:
                logger.error("db_read_error_for_provider_key", provider_key=provider_key, error=str(e), exc_info=True)
                return []

    def deduplicate_events(self, events: List[EventDTO]) -> List[EventDTO]:
        """
        Deduplicate events by event_id.

        Args:
            events: List of EventDTO

        Returns:
            Deduplicated list
        """
        seen = set()
        result = []

        for event in events:
            if event.id not in seen:
                seen.add(event.id)
                result.append(event)

        if len(events) != len(result):
            logger.info("events_deduplicated", original=len(events), deduplicated=len(result))

        return result

    def sort_events_by_commence_time(self, events: List[EventDTO]) -> List[EventDTO]:
        """
        Sort events by commence_time ascending.

        Args:
            events: List of EventDTO

        Returns:
            Sorted list
        """
        try:
            return sorted(
                events,
                key=lambda e: e.commence_time
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

    async def rank(
        self,
        provider_key: str,
        provider: str = "odds_api",
        max_events: int | None = None,
        events: List[EventDTO] | None = None,
    ) -> Dict[str, Any]:
        """
        Rank events using LLM or fallback to date sorting.

        Args:
            provider_key: Provider key
            provider: Provider name
            max_events: Max events override
            events: Pre-fetched EventDTO list (optional, if None will fetch from cache/DB)

        Returns:
            Dict with metrics
        """
        metrics = {
            "processed": 0,
            "llm_batches": 0,
            "errors": 0,
            "fallback_used": False,
        }

        logger.info(
            "ranking_started",
            provider_key=provider_key,
            enabled=self._enabled
        )

        # Use provided events or fetch them
        if events is None:
            events = await self.get_upcoming_events_from_cache(provider_key)

            if not events:
                logger.info("cache_empty_falling_back_to_db")
                # Convert dict to EventDTO for consistency
                events_dict = await self.get_upcoming_events_from_db(max_events or self._max_events)
                # Convert dict to EventDTO with defaults for missing fields
                events = []
                for event_dict in events_dict:
                    # Parse datetime if it's a string
                    commence_time = event_dict.get("commence_time")
                    if isinstance(commence_time, str):
                        from dateutil import parser
                        commence_time = parser.parse(commence_time)
                    else:
                        commence_time = event_dict.get("commence_time")
                    
                    dto = EventDTO(
                        id=UUID(event_dict["id"]),
                        provider=event_dict.get("provider", "odds_api"),
                        external_id=event_dict["external_id"],
                        sport_id=UUID(event_dict["sport_id"]),
                        competition_id=UUID(event_dict["competition_id"]),
                        home_team_id=UUID(event_dict["home_team_id"]) if event_dict.get("home_team_id") else None,
                        away_team_id=UUID(event_dict["away_team_id"]) if event_dict.get("away_team_id") else None,
                        commence_time=commence_time,
                        status=event_dict.get("status", "upcoming"),
                        participant_mode="unknown",
                        participants=[],
                        metadata={},
                        created_at=now_utc(),
                        updated_at=now_utc(),
                    )
                    events.append(dto)

        if not events:
            logger.warning("no_events_to_rank", provider_key=provider_key)
            return metrics

        events = self.deduplicate_events(events)
        events = self.sort_events_by_commence_time(events)
        
        # Build lightweight representation for LLM (only essential fields)
        priority_inputs = self._build_priority_inputs(events)

        if not self._enabled or not self._ai_client:
            logger.info("prioritization_disabled_using_fallback")
            metrics["fallback_used"] = True
            ranked = self._apply_fallback_scores(priority_inputs)
        else:
            try:
                ranked = await self._prioritize_with_llm(priority_inputs, metrics)
            except Exception as e:
                logger.error("llm_prioritization_failed_using_fallback", error=str(e), exc_info=True)
                metrics["fallback_used"] = True
                metrics["errors"] += 1
                ranked = self._apply_fallback_scores(priority_inputs)

        ranked = self._stable_sort_by_priority(ranked)

        await self._write_to_redis(provider_key, ranked)
        await self._write_to_db(provider_key, provider, ranked)

        metrics["processed"] = len(ranked)

        logger.info(
            "ranking_complete",
            provider_key=provider_key,
            processed=metrics["processed"],
            llm_batches=metrics["llm_batches"],
            errors=metrics["errors"],
            fallback_used=metrics["fallback_used"]
        )

        return metrics

    def _build_priority_inputs(self, events: List[EventDTO]) -> List[Dict[str, Any]]:
        """
        Build lightweight event representation for LLM prioritization.
        
        Only includes essential fields needed for prioritization:
        - id (required for score assignment)
        - provider/provider_key (if available)
        - home_team_name -> home_team
        - away_team_name -> away_team
        - commence_time (ISO string)
        - status
        - sport_key (from metadata if available)
        
        Excludes heavy fields like:
        - participants (full list)
        - metadata (full dict)
        - created_at, updated_at, ingested_at, last_seen_at
        - sport_id, competition_id, home_team_id, away_team_id (internal IDs)
        
        Args:
            events: List of EventDTO instances
            
        Returns:
            List of lightweight dict representations for LLM
        """
        result = []
        
        for event in events:
            # Extract sport_key from metadata if available, otherwise use empty string
            sport_key = event.metadata.get("sport_key", "") if event.metadata else ""
            
            # Build minimal representation
            event_dict = {
                "id": str(event.id),
                "provider": event.provider,
                "home_team": event.home_team_name,
                "away_team": event.away_team_name,
                "commence_time": event.commence_time.isoformat() if event.commence_time else "",
                "status": event.status,
                "sport_key": sport_key,
            }
            
            result.append(event_dict)
        
        return result

    def _apply_fallback_scores(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply fallback scoring (date-based).

        Args:
            events: List of events (already sorted by commence_time)

        Returns:
            Events with score added
        """
        for event in events:
            event["score"] = 0.0

        return events

    async def _prioritize_with_llm(
        self,
        events: List[Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Prioritize events using LLM.

        Args:
            events: List of events
            metrics: Metrics dict to update

        Returns:
            Events with scores
        """
        batches = self.batch_events(events)
        all_scores = {}

        for batch in batches:
            try:
                scores = await self._ai_client.prioritize_events(batch)
                metrics["llm_batches"] += 1

                for score_item in scores:
                    all_scores[str(score_item.event_id)] = score_item.score

            except Exception as e:
                logger.error("batch_prioritization_error", error=str(e))
                metrics["errors"] += 1

        for event in events:
            event_id = str(event.get("id"))
            event["score"] = all_scores.get(event_id, 0.0)

        return events

    def _stable_sort_by_priority(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Stable sort: priority DESC, commence_time ASC, event_id ASC.

        Args:
            events: Events with scores

        Returns:
            Sorted events
        """
        return sorted(
            events,
            key=lambda e: (
                -e.get("score", 0.0),
                e.get("commence_time", "9999-12-31T23:59:59"),
                e.get("id", "")
            )
        )

    async def _write_to_redis(self, provider_key: str, events: List[Dict[str, Any]]) -> None:
        """
        Write ranked events to Redis with atomic swap.

        Args:
            provider_key: Provider key
            events: Ranked events
        """
        cache_key = f"priority:events:{provider_key}:ranked"
        temp_key = f"{cache_key}:tmp"

        try:
            pipe = self._redis_cache.pipeline()

            await pipe.delete(temp_key)

            for event in events:
                event_json = json.dumps(event)
                await pipe.rpush(temp_key, event_json)

            await pipe.execute()

            await self._redis_cache.rename(temp_key, cache_key)

            if self._cache_ttl_sec:
                await self._redis_cache.expire(cache_key, self._cache_ttl_sec)

            logger.info(
                "ranked_events_written_to_redis",
                provider_key=provider_key,
                count=len(events),
                cache_ttl_sec=self._cache_ttl_sec
            )

        except Exception as e:
            logger.error("redis_write_failed", provider_key=provider_key, error=str(e))
            try:
                await self._redis_cache.delete(temp_key)
            except Exception:
                pass

    async def _write_to_db(
        self,
        provider_key: str,
        provider: str,
        events: List[Dict[str, Any]],
    ) -> None:
        """
        Write priorities to database.

        Args:
            provider_key: Provider key
            provider: Provider name
            events: Events with scores
        """
        async with self._session_factory() as session:
            repo = EventPriorityRepository(session)

            priorities = [
                {"event_id": e["id"], "score": e.get("score", 0.0)}
                for e in events
            ]

            # Get model from ai_client if available, otherwise use "fallback"
            if not self._enabled or not self._ai_client:
                model = "fallback"
            else:
                model = self._ai_client.model

            count = await repo.upsert_batch(
                provider=provider,
                provider_key=provider_key,
                priorities=priorities,
                model=model,
            )

            await session.commit()

            logger.info(
                "priorities_written_to_db",
                provider_key=provider_key,
                count=count
            )
