"""
Events service for managing event collection targets and processing.
"""
from typing import Literal, List, Dict, Optional
from uuid import UUID
import asyncio
import random
import time
import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from httpx import HTTPStatusError
from app.utils.text_utils import create_team_slug

from app.domain.entities.events.events_targets import EventsTargetsDTO, FilteredReasonDTO
from app.domain.entities.events.events_window import (
    EventsPolicyDTO,
    EventsWindowDTO,
    EventKeyResultDTO,
    EventsRunSummaryDTO,
)
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.repositories.event import EventRepository
from app.infrastructure.repositories.team import TeamRepository

from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.events import EventsCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.domain.entities.events.event import EventDTO
from app.domain.entities.participant import EventUpsertDTO, ParticipantItemDTO
from app.services.participants_helper import build_participants

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
        policy_loader: PolicyLoader,
    ):
        self._odds_client = odds_client
        self._session_factory = session_factory
        self._sports_cache = sports_cache
        self._competitions_cache = competitions_cache
        self._events_cache = events_cache
        self._policy_loader = policy_loader

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

        # Step 1: Get provider from policy and load whitelist
        providers = self._policy_loader.get_providers()
        if not providers:
            logger.warning("no_providers_found_in_policy")
            return EventsTargetsDTO(
                provider="odds_api",
                plan=plan,
                total_in_policy=0,
                total_valid=0,
                filtered_out=[],
                batches=[],
            )
        provider = providers[0]  # Use first provider from policy
        
        # Get competitions from policy
        competitions = self._policy_loader.get_competitions(provider)
        if not competitions:
            logger.warning("no_competitions_found_in_policy", provider=provider)
            return EventsTargetsDTO(
                provider=provider,
                plan=plan,
                total_in_policy=0,
                total_valid=0,
                filtered_out=[],
                batches=[],
            )
        
        # Build whitelist based on plan
        if plan == "free":
            whitelist = sorted(competitions.free)
        elif plan == "pro":
            whitelist = sorted(list(set(competitions.free + competitions.pro)))
        else:  # "all"
            whitelist = sorted(list(set(competitions.free + competitions.pro)))
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
        valid_keys, filtered_out = await self._validate_competitions(whitelist, provider)

        logger.info(
            "competitions_validated",
            plan=plan,
            total_in_policy=total_in_policy,
            valid=len(valid_keys),
            filtered=len(filtered_out),
        )

        # Step 3: Create batches
        # Get batch_size from events policy
        events_policy = self._policy_loader.get_events_policy(provider)
        if not events_policy:
            logger.warning("events_policy_not_found_using_default_batch_size", provider=provider)
            batch_size = 10
        else:
            batch_size = events_policy.batch_size_competitions
        
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

    async def process_events_and_competitions(
        self, provider: str, policy: EventsPolicyDTO, keys: List[str], window: EventsWindowDTO
    ) -> EventsRunSummaryDTO:
        """
        Process competitions with rate limiting and retry logic.

        Args:
            keys: List of slug_keys in exact order to process (no sorting)
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
            is_active = await self._check_competition_active(provider, key)
            if not is_active:
                logger.warning("competition_skipped_inactive", key=key)
                per_key[key] = EventKeyResultDTO(
                    slug_key=key,
                    status="skipped",
                    attempts=0,
                    duration_ms=0,
                    events_count=0,
                )
                skipped += 1
                continue

            # Fetch events with retry
            result, events_data = await self._fetch_events_with_retry(key, window, policy)
            per_key[key] = result

            # Update counters
            if result.status == "success":
                processed += 1
                total_events += result.events_count

                # Convert API events to EventUpsertDTO and save to DB
                try:
                    saved_count = await self._save_events_to_db(provider, key, policy, events_data)
                    logger.info(
                        "events_saved_to_db",
                        key=key,
                        fetched=len(events_data),
                        saved=saved_count
                    )

                    # Refresh cache after successful DB commit
                    await self._refresh_events_cache_for_competition(provider, key)
                except Exception as e:
                    logger.error(
                        "events_save_or_cache_failed",
                        key=key,
                        error=str(e),
                        exc_info=True
                    )
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

            # Rate limit: delay between competitions (except after last one)
            if idx < len(keys) - 1:
                delay = policy.delay_between_competitions_sec
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

    async def check_competition_active(self, category: str, slug_key: str, provider: str) -> bool:
        # TODO: change name method
        """
        Check if competition is active using cache-first approach with DB fallback.

        Priority:
        1. Check competitions cache for slug_key
        2. If cache miss, fallback to DB query
        3. If not found, return False (treat as inactive)

        Args:
            category: Sport category (e.g., 'soccer')
            slug_key: Competition slug_key (e.g., 'soccer_uefa_champs_league')
            provider: Provider name (e.g., 'odds_api')

        Returns:
            True if active, False otherwise
        """
        # Step 1: Try cache
        cached_catalog = await self._competitions_cache.get_catalog(category)

        if cached_catalog and "competitions" in cached_catalog:
            # Cache hit - search for slug_key
            competitions_list = cached_catalog["competitions"]

            for comp_data in competitions_list:
                if comp_data.get("slug_key") == slug_key:
                    is_active = comp_data.get("is_active", False)

                    if is_active:
                        logger.info(
                            "comp_active_check",
                            result=True,
                            source="cache",
                            reason="active",
                            category=category,
                            slug_key=slug_key,
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
                            slug_key=slug_key,
                            provider=provider
                        )
                        return False

            # Found cache but not this slug_key
            logger.info(
                "comp_active_check",
                result=False,
                source="cache",
                reason="not_found_cache",
                category=category,
                slug_key=slug_key,
                provider=provider
            )
        else:
            logger.info(
                "comp_active_cache_miss",
                category=category,
                slug_key=slug_key,
                provider=provider
            )

        # Step 2: DB fallback
        async with self._session_factory() as session:
            event_repo = EventRepository(session)
            db_result = await event_repo.check_competition_active(
                slug_key=slug_key,
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
                    slug_key=slug_key,
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
                    slug_key=slug_key,
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
                    slug_key=slug_key,
                    provider=provider
                )
                return False

    async def _check_competition_active(self, provider: str, slug_key: str) -> bool:
        """
        Check if competition is active using cache-first approach with DB fallback.

        Extracts category (sport) from slug_key, gets provider from policy,
        and uses check_competition_active.

        Args:
            slug_key: Competition slug_key (e.g., 'soccer_uefa_champs_league')

        Returns:
            True if active, False otherwise
        """
        # Extract category from slug_key (e.g., 'soccer_uefa_champs_league' -> 'soccer')
        category = slug_key.split("_")[0] if "_" in slug_key else "unknown"


        is_active = await self.check_competition_active(
            category=category,
            slug_key=slug_key,
            provider=provider
        )

        return is_active

    async def _fetch_events_with_retry(
        self, key: str, window: EventsWindowDTO, policy: EventsPolicyDTO
    ) -> tuple[EventKeyResultDTO, List[Dict]]:
        """
        Fetch events with exponential backoff retry logic.

        Args:
            key: Competition slug_key
            window: Time window for events
            policy: Retry policy configuration

        Returns:
            Tuple of (EventKeyResultDTO with fetch result, list of event dictionaries)
        """
        start_time = time.time()
        attempts = 0
        last_error = None

        for attempt in range(policy.max_attempts):
            attempts = attempt + 1

            try:
                events = await self._odds_client.get_events(
                    slug_key=key,
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

                return (
                    EventKeyResultDTO(
                        slug_key=key,
                        status="success",
                        attempts=attempts,
                        duration_ms=duration_ms,
                        events_count=len(events),
                    ),
                    events,
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
                    return (
                        EventKeyResultDTO(
                            slug_key=key,
                            status="failed",
                            attempts=attempts,
                            duration_ms=duration_ms,
                            events_count=0,
                            error=last_error,
                        ),
                        [],
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

        return (
            EventKeyResultDTO(
                slug_key=key,
                status="failed",
                attempts=attempts,
                duration_ms=duration_ms,
                events_count=0,
                error=last_error,
            ),
            [],
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

    async def _resolve_team_ids(
        self,
        team_repo: "TeamRepository",
        sport_id: UUID,
        provider: str,
        participant_mode: Literal["duel", "solo", "field", "unknown"],
        participants: List[ParticipantItemDTO],
        home_team_name: Optional[str],
        away_team_name: Optional[str],
        has_api_football: bool = False,
        competition_id: Optional[UUID] = None,
        slug_key: Optional[str] = None,
    ) -> tuple[Optional[UUID], Optional[UUID]]:
        """
        Resolve team IDs for event participants based on participant mode.

        Args:
            team_repo: TeamRepository instance
            sport_id: Sport UUID
            provider: Provider name
            participant_mode: Participant mode (duel, solo, field, unknown)
            participants: List of participant DTOs
            home_team_name: Home team name (for duel mode)
            away_team_name: Away team name (for duel mode)
            has_api_football: Whether competition has API-Football coverage
            competition_id: Competition UUID (for logging)
            slug_key: Competition slug_key (for logging)

        Returns:
            Tuple of (home_team_id, away_team_id)
        """
        home_team_id = None
        away_team_id = None

        if participant_mode == "duel":
            # Handle duel mode (home/away)
            if home_team_name:
                team_slug = create_team_slug(home_team_name)
                
                if has_api_football:
                    # For API-Football competitions: only search, don't create
                    team = await team_repo.find_by_slug(sport_id, team_slug)
                    if team:
                        home_team_id = team.id
                    else:
                        logger.warning(
                            "team_not_found_api_football_competition",
                            competition_id=str(competition_id) if competition_id else None,
                            slug_key=slug_key,
                            provider=provider,
                            team_name=home_team_name,
                            team_slug=team_slug,
                            team_role="home",
                        )
                else:
                    # For regular competitions: search and create if not found
                    normalized_home = create_team_slug(home_team_name)
                    home_team_id = await team_repo.resolve_or_create_by_alias(
                        sport_id=sport_id,
                        provider=provider,
                        normalized=normalized_home,
                        raw=home_team_name
                    )

                # Update participants with team_id
                if home_team_id:
                    for p in participants:
                        if p.role == "home":
                            p.team_id = home_team_id

            if away_team_name:
                team_slug = create_team_slug(away_team_name)
                
                if has_api_football:
                    # For API-Football competitions: only search, don't create
                    team = await team_repo.find_by_slug(sport_id, team_slug)
                    if team:
                        away_team_id = team.id
                    else:
                        logger.warning(
                            "team_not_found_api_football_competition",
                            competition_id=str(competition_id) if competition_id else None,
                            slug_key=slug_key,
                            provider=provider,
                            team_name=away_team_name,
                            team_slug=team_slug,
                            team_role="away",
                        )
                else:
                    # For regular competitions: search and create if not found
                    normalized_away = create_team_slug(away_team_name)
                    away_team_id = await team_repo.resolve_or_create_by_alias(
                        sport_id=sport_id,
                        provider=provider,
                        normalized=normalized_away,
                        raw=away_team_name
                    )

                # Update participants with team_id
                if away_team_id:
                    for p in participants:
                        if p.role == "away":
                            p.team_id = away_team_id

        elif participant_mode == "solo":
            # Handle solo mode (single participant)
            if participants and len(participants) > 0:
                solo_name = participants[0].name
                if solo_name:
                    team_slug = create_team_slug(solo_name)
                    
                    if has_api_football:
                        # For API-Football competitions: only search, don't create
                        team = await team_repo.find_by_slug(sport_id, team_slug)
                        if team:
                            participants[0].team_id = team.id
                        else:
                            logger.warning(
                                "team_not_found_api_football_competition",
                                competition_id=str(competition_id) if competition_id else None,
                                slug_key=slug_key,
                                provider=provider,
                                team_name=solo_name,
                                team_slug=team_slug,
                                team_role="solo",
                            )
                    else:
                        # For regular competitions: search and create if not found
                        normalized_solo = create_team_slug(solo_name)
                        solo_team_id = await team_repo.resolve_or_create_by_alias(
                            sport_id=sport_id,
                            provider=provider,
                            normalized=normalized_solo,
                            raw=solo_name
                        )
                        participants[0].team_id = solo_team_id

        # field mode: no team_id resolution

        return home_team_id, away_team_id

    async def _save_events_to_db(
        self, provider: str, slug_key: str, policy: EventsPolicyDTO, events_data: List[Dict]
    ) -> int:
        """
        Convert API events to EventUpsertDTO and save to database (E5).

        If teams_normalization is enabled in policy:
        - Resolves team_id for duel/solo modes via TeamRepository
        - Accumulates aliases in teams.external_ids[provider]
        - Fills home_team_id/away_team_id and participants[*].team_id

        Args:
            provider: Provider name
            slug_key: Competition slug_key
            events_data: List of event dictionaries from API

        Returns:
            Number of successfully saved events
        """
        if not events_data:
            return 0

        saved_count = 0

        async with self._session_factory() as session:
            async with session.begin():
                # Get competition to find sport_id and competition_id
                comp_repo = CompetitionsRepository(session)
                event_repo = EventRepository(session)
                team_repo = TeamRepository(session)
                competition = await comp_repo.get_by_slug_key(
                    provider=provider, slug_key=slug_key
                )

                if not competition:
                    logger.warning(
                        "competition_not_found_for_save",
                        provider=provider,
                        slug_key=slug_key
                    )
                    return 0
                # Save competition IDs while session is active to avoid lazy loading issues
                sport_id = competition.sport_id
                competition_id = competition.id
                
                # Check if competition has API-Football coverage
                has_api_football = bool(
                    competition.api_sources and 
                    competition.api_sources.get("api_football")
                )
                
                # Expunge competition object to avoid lazy loading issues in transaction

                # Check if teams normalization is enabled from policy
                teams_normalization_enabled = policy.teams_normalization_enabled

                # Extract category from slug_key to get participant mode
                category = slug_key.split("_")[0] if "_" in slug_key else "unknown"
                participant_mode_str = self._policy_loader.get_participant_mode_for_sport(
                    provider=provider, sport_key=category
                )
                # Ensure participant_mode is valid Literal type
                valid_modes: Literal["duel", "solo", "field", "unknown"] = (
                    participant_mode_str
                    if participant_mode_str in ("duel", "solo", "field", "unknown")
                    else "unknown"
                )
                participant_mode: Literal["duel", "solo", "field", "unknown"] = valid_modes

                # Convert and save each event within transaction
                for event_data in events_data:
                    try:
                        external_id = event_data.get("id")
                        if not external_id:
                            logger.warning("event_missing_id", slug_key=slug_key)
                            continue

                        # Build participants based on mode
                        participants = build_participants(event_data, participant_mode)

                        # Extract team names
                        home_team_name = event_data.get("home_team")
                        away_team_name = event_data.get("away_team")

                        # E5: Resolve team_id if normalization enabled
                        home_team_id = None
                        away_team_id = None
                        if teams_normalization_enabled:
                            home_team_id, away_team_id = await self._resolve_team_ids(
                                team_repo=team_repo,
                                sport_id=sport_id,
                                provider=provider,
                                participant_mode=participant_mode,
                                participants=participants,
                                home_team_name=home_team_name,
                                away_team_name=away_team_name,
                                has_api_football=has_api_football,
                                competition_id=competition_id,
                                slug_key=slug_key,
                            )

                        # Create EventUpsertDTO
                        dto = EventUpsertDTO(
                            provider=provider,
                            external_id=str(external_id),
                            sport_id=sport_id,
                            competition_id=competition_id,
                            home_team_id=home_team_id,
                            away_team_id=away_team_id,
                            home_team_name=home_team_name,
                            away_team_name=away_team_name,
                            commence_time=event_data.get("commence_time", ""),
                            status="upcoming",
                            participant_mode=participant_mode,
                            participants=participants,
                            metadata={
                                "sport_key": event_data.get("sport_key"),
                                "sport_title": event_data.get("sport_title"),
                            }
                        )

                        # Save event
                        await event_repo.upsert_event(dto)
                        saved_count += 1

                    except Exception as e:
                        logger.error(
                            "failed_to_save_event",
                            provider=provider,
                            slug_key=slug_key,
                            external_id=event_data.get("id"),
                            error=str(e),
                            exc_info=True
                        )
                        continue

        return saved_count

    async def _validate_competitions(
        self, slug_keys: List[str], provider: str
    ) -> tuple[List[str], List[FilteredReasonDTO]]:
        """
        Validate competitions against DB.

        Args:
            slug_keys: List of competition slug_keys to validate
            provider: Provider name (e.g., 'odds_api')

        Returns:
            Tuple of (valid_keys, filtered_out_with_reasons)
        """
        valid_keys = []
        filtered_out = []

        async with self._session_factory() as session:
            comp_repo = CompetitionsRepository(session)

            for slug_key in slug_keys:
                try:
                    # Get competition from DB
                    competition = await get_by_slug_key(
                        provider=provider, slug_key=slug_key
                    )

                    if not competition:
                        filtered_out.append(
                            FilteredReasonDTO(
                                slug_key=slug_key, reason="not_found"
                            )
                        )
                        continue

                    if not competition.is_active:
                        filtered_out.append(
                            FilteredReasonDTO(
                                slug_key=slug_key, reason="inactive"
                            )
                        )
                        continue

                    # Valid competition
                    valid_keys.append(slug_key)

                except Exception as e:
                    logger.error(
                        "competition_validation_error",
                        slug_key=slug_key,
                        error=str(e),
                    )
                    filtered_out.append(
                        FilteredReasonDTO(slug_key=slug_key, reason="not_found")
                    )

        return valid_keys, filtered_out

    async def _refresh_events_cache_for_competition(self, provider: str, slug_key: str) -> None:
        """
        Refresh events cache for a competition atomically.

        Fetches all upcoming events from DB and writes them to cache atomically.

        Args:
            provider: Provider name
            slug_key: Competition slug_key
        """
        # Extract category from slug_key to get competition from cache
        category = slug_key.split("_")[0] if "_" in slug_key else "unknown"

        # Try to get competition from cache first
        competition_id = None
        cached_catalog = await self._competitions_cache.get_catalog(category)
        
        if cached_catalog and "competitions" in cached_catalog:
            competitions_list = cached_catalog["competitions"]
            for comp_data in competitions_list:
                if comp_data.get("slug_key") == slug_key and comp_data.get("provider") == provider:
                    competition_id = comp_data.get("id")
                    if competition_id:
                        # Convert string UUID to UUID object if needed
                        if isinstance(competition_id, str):
                            competition_id = UUID(competition_id)
                        break

        # Fallback to DB if not found in cache
        if not competition_id:
            async with self._session_factory() as session:
                comp_repo = CompetitionsRepository(session)
                competition = await comp_repo.get_by_slug_key(
                    provider=provider, slug_key=slug_key
                )

                if not competition:
                    logger.warning(
                        "cache_refresh_skip_no_competition",
                        provider=provider,
                        slug_key=slug_key
                    )
                    return

                competition_id = competition.id

        # Get all upcoming events for this competition from DB
        async with self._session_factory() as session:
            event_repo = EventRepository(session)
            events_orm = await event_repo.get_upcoming_by_competition(
                competition_id=competition_id,
                provider=provider
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
                    metadata=event.event_metadata or {},
                    created_at=event.created_at,
                    updated_at=event.updated_at,
                    ingested_at=event.ingested_at,
                    last_seen_at=event.last_seen_at
                )
                events_dto.append(dto)

        # Write to cache atomically (outside DB session)
        await self._events_cache.write_upcoming_atomic(
            slug_key=slug_key,
            provider=provider,
            items=events_dto,
            ttl_sec=None
        )

        logger.info(
            "events_cache_refreshed",
            provider=provider,
            slug_key=slug_key,
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

        return batches

    async def get_upcoming_events_from_cache(self) -> List[Dict]:
        """
        Get upcoming events from cache for all enabled competitions (E10).

        Aggregates events from catalog:events:{slug_key}:upcoming cache keys.
        Returns flat list limited by provider_policy.admin.events_view_limit (default 200).

        No filters, no pagination - simple cache read.

        Returns:
            List of event dictionaries from cache
        """
        logger.info("get_upcoming_events_from_cache_started")

        # Get provider from policy and load policy to get competitions and limit
        providers = self._policy_loader.get_providers()
        if not providers:
            logger.warning("no_providers_found_in_policy")
            return []
        provider = providers[0]  # Use first provider from policy

        policy = self._policy_loader.get_events_policy(provider)
        if not policy:
            logger.warning("policy_not_found_for_provider", provider=provider)
            return []
        competitions_free = policy.competitions.get("free", [])
        competitions_pro = policy.competitions.get("pro", [])
        all_competition_keys = list(set(competitions_free + competitions_pro))

        # Get view limit from policy using DTO
        view_limit = policy.events_view_limit

        logger.info(
            "aggregating_events_from_cache",
            competitions_count=len(all_competition_keys),
            view_limit=view_limit
        )

        # Aggregate events from all competitions
        all_events: List[EventDTO] = []
        for slug_key in all_competition_keys:
            try:
                events = await self._events_cache.read_upcoming(slug_key)
                if events:
                    # Use EventDTO objects directly
                    all_events.extend(events)
            except Exception as e:
                logger.warning(
                    "failed_to_read_events_cache",
                    slug_key=slug_key,
                    error=str(e)
                )
                continue

        # Apply limit
        limited_events = all_events[:view_limit]

        logger.info(
            "upcoming_events_aggregated",
            total_events=len(all_events),
            returned_count=len(limited_events),
            limit=view_limit
        )

        # Convert EventDTO to dict for JSON serialization (maintain API interface)
        return [event.model_dump(mode="json") for event in limited_events]
