"""
Events service for managing event collection targets and processing.
"""
from typing import Literal, List
import asyncio
import random
import time
import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from httpx import HTTPStatusError

from app.domain.entities.events_targets import EventsTargetsDTO, FilteredReasonDTO
from app.domain.entities.events_window import (
    EventsPolicyDTO,
    EventsWindowDTO,
    EventKeyResultDTO,
    EventsRunSummaryDTO,
)
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.repositories.event import EventRepository
from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.events import EventsCache
from app.domain.entities.event import EventDTO
from app.config import policy_loader

logger = structlog.get_logger()


class EventsService:
    """Service for managing event collection targets and processing."""

    def __init__(
        self,
        odds_client: OddsAPIClient,
        session_factory: async_sessionmaker[AsyncSession],
        sports_cache: SportsCache,
        competitions_cache: CompetitionsCache,
        events_cache: EventsCache,
        cache_ttl_sec: int = 3600,
    ):
        self._odds_client = odds_client
        self._session_factory = session_factory
        self._sports_cache = sports_cache
        self._competitions_cache = competitions_cache
        self._events_cache = events_cache
        self._cache_ttl_sec = cache_ttl_sec

    async def select_target_competitions(
        self, plan: Literal["free", "pro", "all"] = "all"
    ) -> EventsTargetsDTO:
        """
        Select target competitions for event collection based on policy and DB validation.

        This method:
        1. Loads competition whitelist from policy (free/pro/all)
        2. Validates each competition against DB (exists + is_active)
        3. Filters out invalid competitions with reasons
        4. Creates deterministic batches for processing

        Args:
            plan: Plan filter - 'free' (only free tier), 'pro' (free + pro), 'all' (free + pro)

        Returns:
            EventsTargetsDTO with validated competitions batched for processing
        """
        logger.info("select_target_competitions_started", plan=plan)

        # Step 1: Load whitelist from policy
        provider = "odds_api"
        whitelist = policy_loader.get_competitions_whitelist(provider, plan)
        total_in_policy = len(whitelist)

        logger.info("whitelist_loaded_from_policy", plan=plan, total=total_in_policy)

        if not whitelist:
            logger.warning("empty_whitelist", plan=plan)
            return EventsTargetsDTO(
                provider=provider,
                plan=plan,
                total_in_policy=0,
                total_valid=0,
                filtered_out=[],
                batches=[],
            )

        # Step 2: Validate against DB
        valid_keys, filtered_out = await self._validate_competitions(whitelist)

        logger.info(
            "competitions_validated",
            plan=plan,
            total_in_policy=total_in_policy,
            valid=len(valid_keys),
            filtered=len(filtered_out),
        )

        # Step 3: Create batches
        batch_size = policy_loader.get_batch_size_competitions(provider, default=10)
        batches = self._create_batches(valid_keys, batch_size)

        logger.info(
            "target_competitions_selected",
            plan=plan,
            total_batches=len(batches),
            batch_size=batch_size,
        )

        return EventsTargetsDTO(
            provider=provider,
            plan=plan,
            total_in_policy=total_in_policy,
            total_valid=len(valid_keys),
            filtered_out=filtered_out,
            batches=batches,
        )

    async def process_competitions(
        self, keys: List[str], window: EventsWindowDTO
    ) -> EventsRunSummaryDTO:
        """
        Process competitions with rate limiting and retry logic.

        Args:
            keys: List of provider_keys in exact order to process (no sorting)
            window: Time window for events collection

        Returns:
            EventsRunSummaryDTO with processing results
        """
        logger.info(
            "process_competitions_started",
            total_keys=len(keys),
            from_iso=window.from_iso,
            to_iso=window.to_iso,
        )

        # Load policy
        provider = "odds_api"
        policy_dict = policy_loader.get_events_policy(provider)
        policy = EventsPolicyDTO(**policy_dict)

        # Initialize results
        per_key: dict[str, EventKeyResultDTO] = {}
        processed = 0
        failed = 0
        skipped = 0
        total_events = 0

        # Process each key sequentially (max_concurrency=1)
        for idx, key in enumerate(keys):
            logger.info(
                "processing_competition",
                key=key,
                index=idx + 1,
                total=len(keys),
            )

            # Check if competition is active
            is_active = await self._check_competition_active(key)
            if not is_active:
                logger.warning("competition_skipped_inactive", key=key)
                per_key[key] = EventKeyResultDTO(
                    provider_key=key,
                    status="skipped",
                    attempts=0,
                    duration_ms=0,
                    events_count=0,
                )
                skipped += 1
                continue

            # Fetch events with retry
            result = await self._fetch_events_with_retry(key, window, policy)
            per_key[key] = result

            # Update counters
            if result.status == "success":
                processed += 1
                total_events += result.events_count
            elif result.status == "failed":
                failed += 1
            elif result.status == "skipped":
                skipped += 1

            logger.info(
                "competition_processed",
                key=key,
                status=result.status,
                attempts=result.attempts,
                duration_ms=result.duration_ms,
                events_count=result.events_count,
            )

            # Refresh cache atomically for this competition after successful processing
            if result.status == "success":
                try:
                    await self._refresh_events_cache_for_competition(key)
                except Exception as e:
                    logger.error(
                        "cache_refresh_failed",
                        key=key,
                        error=str(e),
                        exc_info=True
                    )

            # Rate limit: delay between competitions (except after last one)
            if idx < len(keys) - 1:
                delay = policy.delay_between_competitions_sec
                logger.debug("rate_limit_delay", delay_sec=delay)
                await asyncio.sleep(delay)

        summary = EventsRunSummaryDTO(
            processed=processed,
            failed=failed,
            skipped=skipped,
            total_events=total_events,
            per_key=per_key,
        )

        logger.info(
            "process_competitions_completed",
            processed=processed,
            failed=failed,
            skipped=skipped,
            total_events=total_events,
        )

        return summary

    async def check_competition_active(self, category: str, provider_key: str, provider: str) -> bool:
        """
        Check if competition is active using cache-first approach with DB fallback.

        Priority:
        1. Check competitions cache for provider_key
        2. If cache miss, fallback to DB query
        3. If not found, return False (treat as inactive)

        Args:
            category: Sport category (e.g., 'soccer')
            provider_key: Competition provider_key (e.g., 'soccer_uefa_champs_league')
            provider: Provider name (e.g., 'odds_api')

        Returns:
            True if active, False otherwise
        """
        # Step 1: Try cache
        cached_catalog = await self._competitions_cache.get_catalog(category)

        if cached_catalog and "competitions" in cached_catalog:
            # Cache hit - search for provider_key
            competitions_list = cached_catalog["competitions"]

            for comp_data in competitions_list:
                if comp_data.get("provider_key") == provider_key:
                    is_active = comp_data.get("is_active", False)

                    if is_active:
                        logger.info(
                            "comp_active_check",
                            result=True,
                            source="cache",
                            reason="active",
                            category=category,
                            provider_key=provider_key,
                            provider=provider
                        )
                        return True
                    else:
                        logger.info(
                            "comp_active_check",
                            result=False,
                            source="cache",
                            reason="inactive",
                            category=category,
                            provider_key=provider_key,
                            provider=provider
                        )
                        return False

            # Found cache but not this provider_key
            logger.info(
                "comp_active_check",
                result=False,
                source="cache",
                reason="not_found_cache",
                category=category,
                provider_key=provider_key,
                provider=provider
            )
        else:
            logger.info(
                "comp_active_cache_miss",
                category=category,
                provider_key=provider_key,
                provider=provider
            )

        # Step 2: DB fallback
        async with self._session_factory() as session:
            event_repo = EventRepository(session)
            db_result = await event_repo.check_competition_active(
                provider_key=provider_key,
                provider=provider
            )

            if db_result is None:
                # Not found in DB
                logger.info(
                    "comp_active_check",
                    result=False,
                    source="db",
                    reason="not_found_db",
                    category=category,
                    provider_key=provider_key,
                    provider=provider
                )
                return False
            elif db_result:
                # Active in DB
                logger.info(
                    "comp_active_check",
                    result=True,
                    source="db",
                    reason="active",
                    category=category,
                    provider_key=provider_key,
                    provider=provider
                )
                return True
            else:
                # Inactive in DB
                logger.info(
                    "comp_active_check",
                    result=False,
                    source="db",
                    reason="inactive",
                    category=category,
                    provider_key=provider_key,
                    provider=provider
                )
                return False

    async def _check_competition_active(self, provider_key: str) -> bool:
        """
        Check if competition is active using cache-first approach with DB fallback.

        Extracts category (sport) from provider_key, gets provider from policy,
        and uses check_competition_active.

        Args:
            provider_key: Competition provider_key (e.g., 'soccer_uefa_champs_league')

        Returns:
            True if active, False otherwise
        """
        # Extract category from provider_key (e.g., 'soccer_uefa_champs_league' -> 'soccer')
        category = provider_key.split("_")[0] if "_" in provider_key else "unknown"

        # Get provider from policy
        policy_dict = policy_loader.get_events_policy(provider="odds_api")
        provider = policy_dict.get("provider", "odds_api")

        is_active = await self.check_competition_active(
            category=category,
            provider_key=provider_key,
            provider=provider
        )

        return is_active

    async def _fetch_events_with_retry(
        self, key: str, window: EventsWindowDTO, policy: EventsPolicyDTO
    ) -> EventKeyResultDTO:
        """
        Fetch events with exponential backoff retry logic.

        Args:
            key: Competition provider_key
            window: Time window for events
            policy: Retry policy configuration

        Returns:
            EventKeyResultDTO with fetch result
        """
        start_time = time.time()
        attempts = 0
        last_error = None

        for attempt in range(policy.max_attempts):
            attempts = attempt + 1

            try:
                logger.debug(
                    "fetch_attempt",
                    key=key,
                    attempt=attempts,
                    max_attempts=policy.max_attempts,
                )

                events = await self._odds_client.get_events(
                    provider_key=key,
                    from_iso=window.from_iso,
                    to_iso=window.to_iso,
                )

                duration_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    "fetch_success",
                    key=key,
                    attempts=attempts,
                    events_count=len(events),
                    duration_ms=duration_ms,
                )

                return EventKeyResultDTO(
                    provider_key=key,
                    status="success",
                    attempts=attempts,
                    duration_ms=duration_ms,
                    events_count=len(events),
                )

            except HTTPStatusError as e:
                status_code = e.response.status_code
                last_error = f"HTTP {status_code}: {str(e)}"

                logger.warning(
                    "fetch_http_error",
                    key=key,
                    attempt=attempts,
                    status_code=status_code,
                    error=str(e),
                )

                # Check if status is retriable
                if status_code not in policy.retriable_statuses:
                    logger.error(
                        "fetch_non_retriable_status",
                        key=key,
                        status_code=status_code,
                        attempts=attempts,
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    return EventKeyResultDTO(
                        provider_key=key,
                        status="failed",
                        attempts=attempts,
                        duration_ms=duration_ms,
                        events_count=0,
                        error=last_error,
                    )

                # Calculate backoff delay for next attempt
                if attempt < policy.max_attempts - 1:
                    delay = self._calculate_backoff_delay(
                        attempt=attempt,
                        base_delay=policy.base_delay_sec,
                        max_delay=policy.max_delay_sec,
                        jitter=policy.jitter,
                    )
                    logger.info("retry_backoff_delay", key=key, delay_sec=delay, attempt=attempts)
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error = str(e)
                logger.error(
                    "fetch_unexpected_error",
                    key=key,
                    attempt=attempts,
                    error=str(e),
                    exc_info=True,
                )

                # Calculate backoff delay for next attempt
                if attempt < policy.max_attempts - 1:
                    delay = self._calculate_backoff_delay(
                        attempt=attempt,
                        base_delay=policy.base_delay_sec,
                        max_delay=policy.max_delay_sec,
                        jitter=policy.jitter,
                    )
                    logger.info("retry_backoff_delay", key=key, delay_sec=delay, attempt=attempts)
                    await asyncio.sleep(delay)

        # All attempts exhausted
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "fetch_all_attempts_exhausted",
            key=key,
            attempts=attempts,
            error=last_error,
        )

        return EventKeyResultDTO(
            provider_key=key,
            status="failed",
            attempts=attempts,
            duration_ms=duration_ms,
            events_count=0,
            error=last_error,
        )

    def _calculate_backoff_delay(
        self, attempt: int, base_delay: int, max_delay: int, jitter: bool
    ) -> float:
        """
        Calculate exponential backoff delay with optional jitter.

        Args:
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * 2^attempt
        delay = min(base_delay * (2 ** attempt), max_delay)

        # Add jitter if enabled
        if jitter:
            # Jitter: +/- 10% of delay
            jitter_amount = delay * 0.1
            delay = delay + random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    async def _validate_competitions(
        self, provider_keys: List[str]
    ) -> tuple[List[str], List[FilteredReasonDTO]]:
        """
        Validate competitions against DB.

        Args:
            provider_keys: List of competition provider_keys to validate

        Returns:
            Tuple of (valid_keys, filtered_out_with_reasons)
        """
        valid_keys = []
        filtered_out = []

        async with self._session_factory() as session:
            comp_repo = CompetitionsRepository(session)

            for provider_key in provider_keys:
                try:
                    # Get competition from DB
                    competition = await comp_repo.get_by_provider_key(
                        provider="odds_api", provider_key=provider_key
                    )

                    if not competition:
                        logger.debug(
                            "competition_not_found_in_db", provider_key=provider_key
                        )
                        filtered_out.append(
                            FilteredReasonDTO(
                                provider_key=provider_key, reason="not_found"
                            )
                        )
                        continue

                    if not competition.is_active:
                        logger.debug(
                            "competition_inactive", provider_key=provider_key
                        )
                        filtered_out.append(
                            FilteredReasonDTO(
                                provider_key=provider_key, reason="inactive"
                            )
                        )
                        continue

                    # Valid competition
                    valid_keys.append(provider_key)
                    logger.debug(
                        "competition_validated", provider_key=provider_key
                    )

                except Exception as e:
                    logger.error(
                        "competition_validation_error",
                        provider_key=provider_key,
                        error=str(e),
                    )
                    filtered_out.append(
                        FilteredReasonDTO(provider_key=provider_key, reason="not_found")
                    )

        return valid_keys, filtered_out

    async def _refresh_events_cache_for_competition(self, provider_key: str) -> None:
        """
        Refresh events cache for a competition atomically.

        Fetches all upcoming events from DB and writes them to cache atomically.

        Args:
            provider_key: Competition provider_key
        """
        async with self._session_factory() as session:
            # Get competition to find competition_id
            comp_repo = CompetitionsRepository(session)
            competition = await comp_repo.get_by_provider_key(
                provider="odds_api", provider_key=provider_key
            )

            if not competition:
                logger.warning(
                    "cache_refresh_skip_no_competition",
                    provider_key=provider_key
                )
                return

            # Get all upcoming events for this competition
            event_repo = EventRepository(session)
            events_orm = await event_repo.get_upcoming_by_competition(
                competition_id=competition.id,
                provider="odds_api"
            )

            # Convert ORM to DTO
            events_dto = []
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
                    metadata=event.metadata or {},
                    created_at=event.created_at,
                    updated_at=event.updated_at,
                    ingested_at=event.ingested_at,
                    last_seen_at=event.last_seen_at
                )
                events_dto.append(dto)

            # Write to cache atomically
            await self._events_cache.write_upcoming_atomic(
                provider_key=provider_key,
                items=events_dto,
                ttl_sec=self._cache_ttl_sec
            )

            logger.info(
                "events_cache_refreshed",
                provider_key=provider_key,
                upcoming_count=len(events_dto)
            )

    def _create_batches(self, items: List[str], batch_size: int) -> List[List[str]]:
        """
        Create deterministic batches from list of items.

        Args:
            items: List of items to batch (already sorted)
            batch_size: Size of each batch

        Returns:
            List of batches
        """
        if not items or batch_size <= 0:
            return []

        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batches.append(batch)

        logger.debug("batches_created", total_items=len(items), batch_size=batch_size, total_batches=len(batches))
        return batches
