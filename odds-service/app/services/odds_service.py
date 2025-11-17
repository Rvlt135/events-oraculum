import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from uuid import UUID
from collections import defaultdict

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import structlog

from app.utils.odds_math import safe_avg, safe_best

if TYPE_CHECKING:
    from app.domain.entities.events_window import EventsWindowDTO

from app.infrastructure.cache.catalog.events import EventsCache
from app.infrastructure.cache.catalog.odds import OddsCache
from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.config.policy_loader import PolicyLoader
from app.domain.policy.dto import OddsPolicyDTO
from app.utils.time_utils import now_utc, parse_utc, build_events_window
from app.infrastructure.repositories import (
    TeamRepository,
    EventRepository,
    BookmakerRepository,
    OddsSnapshotRepository,
    NormalizedOddsRepository,
    CompetitionsRepository,
)
from app.domain.entities.odds import (
    EventShortDTO,
    CompetitionOddsDTO,
    EventOddsDTO,
    EventBookmakerMarketOddsDTO,
    OddsOutcomeDTO,
    BookmakerDTO,
    ExternalOddsEventDTO,
    OddsSnapshotDTO,
    NormalizedOddsDTO,
)
from app.domain.entities.events_window import EventsWindowDTO

logger = structlog.get_logger()


class OddsService:
    def __init__(self,
                 odds_client: OddsAPIClient,
                 session_factory: async_sessionmaker[AsyncSession],
                 redis_cache: redis.Redis,
                 events_cache: EventsCache,
                 odds_cache: OddsCache,
                 policy_loader: PolicyLoader,
                 ) -> None:
        self.session_factory = session_factory
        self.odds_client = odds_client
        self.redis_cache = redis_cache
        self.events_cache = events_cache
        self.odds_cache = odds_cache
        self.policy_loader = policy_loader


    @staticmethod
    def normalize_team_name(name: str) -> str:
        normalized = name.lower().strip()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", "_", normalized)
        return normalized

    def calculate_odds_stats(
        self, outcomes: List[Dict[str, Any]]
    ) -> Tuple[float, float, Optional[float], float, float, Optional[float], int, datetime]:
        """
        DEPRECATED: Use aggregate_to_normalized instead.

        This method works with raw dict and is replaced by DTO-based normalization.
        """
        home_odds: List[float] = []
        away_odds: List[float] = []
        draw_odds: List[float] = []
        latest_timestamp = now_utc()

        for outcome in outcomes:
            name = outcome.get("name", "").lower()
            price = float(outcome.get("price", 0))

            if "draw" in name or name == "draw":
                draw_odds.append(price)
            elif len(home_odds) == 0:
                home_odds.append(price)
            else:
                away_odds.append(price)

        home_avg = sum(home_odds) / len(home_odds) if home_odds else 0.0
        away_avg = sum(away_odds) / len(away_odds) if away_odds else 0.0
        draw_avg = sum(draw_odds) / len(draw_odds) if draw_odds else None

        home_best = max(home_odds) if home_odds else 0.0
        away_best = max(away_odds) if away_odds else 0.0
        draw_best = max(draw_odds) if draw_odds else None

        bookmakers_count = len(outcomes) // 2 if len(outcomes) >= 2 else 1

        return (
            home_avg,
            away_avg,
            draw_avg,
            home_best,
            away_best,
            draw_best,
            bookmakers_count,
            latest_timestamp,
        )

    async def process_event_data(
        self, event_data: Dict[str, Any], sport_id: UUID, competition_id: UUID
    ) -> Optional[UUID]:
        """
        DEPRECATED: Use fetch_odds_for_competition + normalize_to_snapshots instead.

        This method works with raw dict and writes to DB directly.
        It's replaced by DTO-based flow: fetch -> normalize -> aggregate.
        """
        external_id = event_data.get("id")
        home_team_name = event_data.get("home_team")
        away_team_name = event_data.get("away_team")
        commence_time_str = event_data.get("commence_time")
        try:

            if not all([external_id, home_team_name, away_team_name, commence_time_str]):
                logger.warning("missing_event_data", external_id=external_id)
                return None

            commence_time = parse_utc(commence_time_str)
            async with self.session_factory() as session:
                async with session.begin():
                    team_repo = TeamRepository(session)
                    event_repo = EventRepository(session)
                    bookmaker_repo = BookmakerRepository(session)
                    snapshot_repo = OddsSnapshotRepository(session)
                    normalized_repo = NormalizedOddsRepository(session)

                    home_team_id, away_team_id = await self.create_home_team_and_away_team_in_db(team_repo, home_team_name, away_team_name, sport_id, external_id)

                    event_id = await event_repo.create_or_update(
                        external_id=external_id,
                        sport_id=sport_id,
                        competition_id=competition_id,
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        commence_time=commence_time,
                        status="upcoming",
                        event_metadata={"sport_key": event_data.get("sport_key")},
                    )

                    timestamp_ingested = now_utc()

                    bookmakers = event_data.get("bookmakers", [])
                    all_outcomes: List[Dict[str, Any]] = []

                    for bookmaker_data in bookmakers:
                        bookmaker_key = bookmaker_data.get("key")
                        bookmaker_name = bookmaker_data.get("title")

                        if not bookmaker_key or not bookmaker_name:
                            continue

                        bookmaker_id = await bookmaker_repo.get_or_create_by_key(
                            key=bookmaker_key,
                            name=bookmaker_name,
                            region="eu",
                        )

                        markets = bookmaker_data.get("markets", [])
                        for market in markets:
                            market_type = market.get("key")
                            outcomes = market.get("outcomes", [])

                            if not market_type or not outcomes:
                                continue

                            last_update_str = market.get("last_update")
                            last_update = (
                                parse_utc(last_update_str)
                                if last_update_str
                                else now_utc()
                            )

                            await snapshot_repo.create_snapshot(
                                event_id=event_id,
                                bookmaker_id=bookmaker_id,
                                market_type=market_type,
                                outcomes={"outcomes": outcomes},
                                timestamp_source=last_update,
                            )

                            if market_type == "h2h":
                                all_outcomes.extend(outcomes)

                    if all_outcomes:
                        (
                            home_avg,
                            away_avg,
                            draw_avg,
                            home_best,
                            away_best,
                            draw_best,
                            bookmakers_count,
                            timestamp_source,
                        ) = self.calculate_odds_stats(all_outcomes)

                        await normalized_repo.create_normalized(
                            event_id=event_id,
                            market_type="h2h",
                            home_odds_avg=home_avg,
                            away_odds_avg=away_avg,
                            draw_odds_avg=draw_avg,
                            home_odds_best=home_best,
                            away_odds_best=away_best,
                            draw_odds_best=draw_best,
                            bookmakers_count=bookmakers_count,
                            timestamp_source=timestamp_source,
                            timestamp_ingested=timestamp_ingested,
                        )

                    logger.info("processed_event", event_id=str(event_id), external_id=external_id)
            return event_id

        except Exception as e:
            logger.error("error_processing_event", error=str(e), external_id=external_id)
            return None

    async def create_home_team_and_away_team_in_db(self,team_repo: TeamRepository, home_team_name: str, away_team_name: str,
                                                   sport_id: UUID, external_id: str) -> tuple[UUID, UUID]:
                home_team_id = await team_repo.get_or_create(
                    name=home_team_name,
                    normalized_name=self.normalize_team_name(home_team_name),
                    sport_id=sport_id,
                    external_ids={"odds_api": external_id},
                )

                away_team_id = await team_repo.get_or_create(
                    name=away_team_name,
                    normalized_name=self.normalize_team_name(away_team_name),
                    sport_id=sport_id,
                    external_ids={"odds_api": external_id},
                )
                return home_team_id, away_team_id

    async def get_competitions_for_odds(
        self,
        provider: str,
        policy_keys: list[str],
        window: "EventsWindowDTO",
    ) -> list[str]:
        """
        Get list of provider_key for odds based on policy keys and actual upcoming events.

        Returns intersection of:
        - Policy whitelist (provided policy_keys)
        - Actual upcoming events (from cache or DB)

        Args:
            provider: Provider name (e.g., 'odds_api')
            policy_keys: List of provider_key from policy whitelist
            window: EventsWindowDTO with time window for filtering

        Returns:
            Sorted list of provider_key that have upcoming events
        """
        logger.info(
            "get_competitions_for_odds_started",
            provider=provider,
            policy_keys_count=len(policy_keys)
        )

        if not policy_keys:
            logger.warning("empty_policy_keys", provider=provider)
            return []

        policy_keys_set = set(policy_keys)
        has_upcoming_keys: set[str] = set()

        from_dt = parse_utc(window.from_iso)
        to_dt = parse_utc(window.to_iso)

        # Step 1: Try cache first
        for provider_key in policy_keys_set:
            try:
                events = await self.events_cache.read_upcoming(provider_key)
            except Exception as e:
                logger.debug(
                    "cache_read_error_for_key",
                    provider_key=provider_key,
                    error=str(e)
                )
                continue

            if not events:
                continue

            count_in_window = sum(
                1 for e in events
                if from_dt <= e.commence_time <= to_dt
            )
            if not count_in_window:
                continue

            has_upcoming_keys.add(provider_key)
            logger.debug(
                "upcoming_events_found_in_cache",
                provider_key=provider_key,
                count=count_in_window,
            )

        # Step 2: Fallback to DB for keys not found in cache
        cache_miss_keys = policy_keys_set - has_upcoming_keys
        if cache_miss_keys:
            logger.info(
                "checking_db_for_cache_miss_keys",
                count=len(cache_miss_keys)
            )

            async with self.session_factory() as session:
                comp_repo = CompetitionsRepository(session)
                event_repo = EventRepository(session)

                for provider_key in cache_miss_keys:
                    try:
                        competition = await comp_repo.get_by_provider_key(
                            provider=provider,
                            provider_key=provider_key
                        )
                    except Exception as e:
                        logger.warning(
                            "db_check_error_for_key",
                            provider_key=provider_key,
                            error=str(e)
                        )
                        continue
                    if not competition:
                        logger.debug(
                            "competition_not_found_in_db",
                            provider_key=provider_key
                        )
                        continue
                    try:
                        events_orm = await event_repo.get_upcoming_by_competition(
                            competition_id=competition.id,
                            provider=provider
                        )
                    except Exception as e:
                        logger.warning(
                            "db_events_lookup_failed",
                            provider_key=provider_key,
                            competition_id=str(competition.id),
                            error=str(e),
                        )
                        continue
                    count_in_window = sum(
                        1 for e in events_orm
                        if from_dt <= e.commence_time <= to_dt
                    )

                    if not count_in_window:
                        continue

                    has_upcoming_keys.add(provider_key)
                    logger.debug(
                        "upcoming_events_found_in_db",
                        provider_key=provider_key,
                        count=count_in_window,
                    )

        # Step 3: Final list - intersection
        keys_for_odds = sorted(policy_keys_set & has_upcoming_keys)

        # Step 4: Logging
        dropped_keys = policy_keys_set - has_upcoming_keys
        logger.info(
            "get_competitions_for_odds_completed",
            provider=provider,
            total_policy_keys=len(policy_keys_set),
            total_has_upcoming=len(has_upcoming_keys),
            final_count=len(keys_for_odds),
            dropped_count=len(dropped_keys)
        )

        if dropped_keys:
            logger.debug(
                "dropped_keys_no_upcoming_events",
                provider=provider,
                dropped_keys=sorted(dropped_keys)
            )

        return keys_for_odds

    def _get_time_window_from_events_policy(self, provider: str) -> EventsWindowDTO:
        """
        Get time window from events policy using same helper as events collection.

        Args:
            provider: Provider name

        Returns:
            EventsWindowDTO with time window
        """
        events_policy = self.policy_loader.get_events_policy(provider)
        if not events_policy:
            raise ValueError(f"Events policy not found for provider: {provider}")

        period_days = events_policy.period
        from_iso, to_iso = build_events_window(period_days)

        return EventsWindowDTO(
            from_iso=from_iso,
            to_iso=to_iso,
            period_days=period_days
        )

    async def _resolve_bookmaker_dto(
        self,
        bookmaker_key: str,
        bookmaker_title: str | None,
    ) -> BookmakerDTO:
        """
        Resolve BookmakerDTO from bookmaker key.

        Tries to get from DB, if not found creates minimal DTO.

        Args:
            bookmaker_key: Bookmaker key from external API
            bookmaker_title: Bookmaker title from external API

        Returns:
            BookmakerDTO
        """
        async with self.session_factory() as session:
            bookmaker_repo = BookmakerRepository(session)
            bookmaker = await bookmaker_repo.get_by_key(bookmaker_key)

            if bookmaker:
                return BookmakerDTO(
                    id=bookmaker.id,
                    key=bookmaker.key,
                    name=bookmaker.name,
                    region=bookmaker.region,
                    is_active=bookmaker.is_active,
                    created_at=bookmaker.created_at,
                )

        # Minimal DTO if not found in DB
        return BookmakerDTO(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            key=bookmaker_key,
            name=bookmaker_title or bookmaker_key,
            region="unknown",
            is_active=True,
            created_at=now_utc(),
        )

    async def _map_external_odds_to_competition_odds(
        self,
        external_events: list[ExternalOddsEventDTO],
        upcoming_events: list[EventShortDTO],
        provider_key: str,
    ) -> CompetitionOddsDTO:
        """
        Map ExternalOddsEventDTO to CompetitionOddsDTO, filtering by upcoming events.

        Args:
            external_events: List of external odds events from API
            upcoming_events: List of our local upcoming events
            provider_key: Competition provider key

        Returns:
            CompetitionOddsDTO with filtered and mapped events
        """
        # Build map: external_id -> event_id
        external_id_to_event_id: dict[str, UUID] = {
            event.external_id: event.event_id
            for event in upcoming_events
        }

        external_ids_set = set(external_id_to_event_id.keys())

        event_odds_list: list[EventOddsDTO] = []

        for external_event in external_events:
            if not external_event.id:
                continue

            external_id = external_event.id

            # Filter: only events that exist in our local events
            if external_id not in external_ids_set:
                logger.info(
                    "odds_event_not_in_local_events",
                    external_id=external_id,
                    provider_key=provider_key
                )
                continue

            event_id = external_id_to_event_id[external_id]

            # Map markets
            markets: list[EventBookmakerMarketOddsDTO] = []

            for external_bookmaker in external_event.bookmakers:
                if not external_bookmaker.key:
                    continue

                bookmaker_dto = await self._resolve_bookmaker_dto(
                    bookmaker_key=external_bookmaker.key,
                    bookmaker_title=external_bookmaker.title,
                )

                for external_market in external_bookmaker.markets:
                    if not external_market.key:
                        continue

                    # Map outcomes
                    outcomes: list[OddsOutcomeDTO] = []
                    for external_outcome in external_market.outcomes:
                        if external_outcome.name is None or external_outcome.price is None:
                            continue

                        outcome = OddsOutcomeDTO(
                            name=external_outcome.name,
                            role="unknown",
                            team_id=None,
                            price=external_outcome.price,
                            provider_name=external_bookmaker.key,
                            sid=external_outcome.sid,
                            bet_limit=(
                                {"value": external_outcome.bet_limit}
                                if external_outcome.bet_limit is not None
                                else None
                            ),
                        )
                        outcomes.append(outcome)

                    if outcomes:
                        market_odds = EventBookmakerMarketOddsDTO(
                            bookmaker=bookmaker_dto,
                            market_type=external_market.key,
                            last_update=external_market.last_update,
                            outcomes=outcomes,
                        )
                        markets.append(market_odds)

            if markets:
                event_odds = EventOddsDTO(
                    event_id=event_id,
                    external_id=external_id,
                    provider_key=provider_key,
                    commence_time=external_event.commence_time,
                    home_team=external_event.home_team,
                    away_team=external_event.away_team,
                    markets=markets,
                )
                event_odds_list.append(event_odds)
            else:
                logger.info(
                    "odds_missing_for_event",
                    external_id=external_id,
                    provider_key=provider_key
                )

        return CompetitionOddsDTO(
            provider_key=provider_key,
            events=event_odds_list,
        )

    async def fetch_odds_for_competition(
        self,
        provider: str,
        provider_key: str,
        upcoming_events: list[EventShortDTO],
    ) -> CompetitionOddsDTO:
        """
        Fetch odds for competition from external API and filter by our upcoming events.

        Args:
            provider: Provider name (e.g., 'odds_api')
            provider_key: Competition provider key (sport_key for external API)
            upcoming_events: List of our local upcoming events

        Returns:
            CompetitionOddsDTO with filtered odds (empty if no upcoming events)
        """
        logger.info(
            "fetch_odds_for_competition_started",
            provider=provider,
            provider_key=provider_key,
            upcoming_events_count=len(upcoming_events)
        )

        if not upcoming_events:
            logger.warning(
                "no_upcoming_events_for_odds",
                provider=provider,
                provider_key=provider_key
            )
            return CompetitionOddsDTO(
                provider_key=provider_key,
                events=[],
            )

        # Get odds policy
        odds_policy = self.policy_loader.get_odds_policy(provider)
        if not odds_policy:
            logger.warning(
                "odds_policy_not_found",
                provider=provider,
                provider_key=provider_key
            )
            return CompetitionOddsDTO(
                provider_key=provider_key,
                events=[],
            )

        # Get time window from events policy (same as events collection)
        window = self._get_time_window_from_events_policy(provider)

        # Call external API
        try:
            raw_odds_data = await self.odds_client.fetch_odds(
                sport=provider_key,
                regions=odds_policy.regions,
                markets=odds_policy.markets,
                commence_time_from=window.from_iso,
                commence_time_to=window.to_iso,
                bookmakers=odds_policy.bookmakers,
                include_links=odds_policy.include_links,
                include_sids=odds_policy.include_sids,
                include_bet_limits=odds_policy.include_bet_limits,
                include_rotation_numbers=odds_policy.include_rotation_numbers,
                date_format="iso",
                odds_format="decimal",
            )

            # Parse external events
            external_events: list[ExternalOddsEventDTO] = []
            for event_data in raw_odds_data:
                try:
                    external_event = ExternalOddsEventDTO.model_validate(event_data)
                    external_events.append(external_event)
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_external_odds_event",
                        provider_key=provider_key,
                        event_data=event_data,
                        error=str(e)
                    )
                    continue

            # Map and filter
            result = await self._map_external_odds_to_competition_odds(
                external_events=external_events,
                upcoming_events=upcoming_events,
                provider_key=provider_key,
            )

            logger.info(
                "fetch_odds_for_competition_completed",
                provider=provider,
                provider_key=provider_key,
                external_events_count=len(external_events),
                filtered_events_count=len(result.events)
            )

            return result

        except Exception as e:
            logger.error(
                "fetch_odds_for_competition_failed",
                provider=provider,
                provider_key=provider_key,
                error=str(e),
                exc_info=True
            )
            return CompetitionOddsDTO(
                provider_key=provider_key,
                events=[],
            )

    def normalize_to_snapshots(
        self,
        competition_odds: CompetitionOddsDTO,
        odds_policy: Optional[OddsPolicyDTO] = None,
    ) -> list[OddsSnapshotDTO]:
        """
        Normalize CompetitionOddsDTO to list of OddsSnapshotDTO.

        Converts provider-level odds data to snapshot DTOs without DB writes.
        Filters by policy.markets and policy.bookmakers if policy is provided.

        Args:
            competition_odds: CompetitionOddsDTO from fetch_odds_for_competition
            odds_policy: Optional OddsPolicyDTO for filtering markets and bookmakers

        Returns:
            List of OddsSnapshotDTO (without id, created_at - will be set on persist)
        """
        logger.info(
            "normalize_to_snapshots_started",
            provider_key=competition_odds.provider_key,
            events_count=len(competition_odds.events),
            has_policy=odds_policy is not None
        )

        # Use policy markets if provided, otherwise fallback to default supported markets
        if odds_policy and odds_policy.markets:
            allowed_markets = set(odds_policy.markets)
        else:
            allowed_markets = {"h2h", "totals", "spreads"}
        
        # Use policy bookmakers if provided
        allowed_bookmakers = set(odds_policy.bookmakers) if odds_policy and odds_policy.bookmakers else None

        snapshots: list[OddsSnapshotDTO] = []
        skipped_markets = 0
        skipped_bookmakers = 0
        skipped_events = 0
        timestamp_ingested = now_utc()

        for event_odds in competition_odds.events:
            if not event_odds.markets:
                skipped_events += 1
                continue

            for market_odds in event_odds.markets:
                market_type = market_odds.market_type

                # Filter by allowed markets from policy
                if market_type not in allowed_markets:
                    logger.debug(
                        "market_filtered_by_policy",
                        provider_key=competition_odds.provider_key,
                        event_id=str(event_odds.event_id),
                        market_type=market_type,
                        allowed_markets=list(allowed_markets)
                    )
                    skipped_markets += 1
                    continue

                # Filter by allowed bookmakers from policy
                bookmaker_key = market_odds.bookmaker.key if market_odds.bookmaker else None
                if allowed_bookmakers is not None and bookmaker_key not in allowed_bookmakers:
                    logger.debug(
                        "bookmaker_filtered_by_policy",
                        provider_key=competition_odds.provider_key,
                        event_id=str(event_odds.event_id),
                        market_type=market_type,
                        bookmaker_key=bookmaker_key,
                        allowed_bookmakers=list(allowed_bookmakers)
                    )
                    skipped_bookmakers += 1
                    continue

                if not market_odds.outcomes:
                    continue

                timestamp_source = market_odds.last_update or timestamp_ingested

                snapshot = OddsSnapshotDTO(
                    id=None,
                    event_id=event_odds.event_id,
                    bookmaker_id=market_odds.bookmaker.id,
                    market_type=market_type,
                    outcomes=market_odds.outcomes,
                    timestamp_source=timestamp_source,
                    timestamp_ingested=timestamp_ingested,
                    created_at=None,
                )
                snapshots.append(snapshot)

        logger.info(
            "normalize_to_snapshots_completed",
            provider_key=competition_odds.provider_key,
            snapshots_count=len(snapshots),
            skipped_markets=skipped_markets,
            skipped_bookmakers=skipped_bookmakers,
            skipped_events=skipped_events
        )

        return snapshots

    def aggregate_to_normalized(
        self,
        snapshots: list[OddsSnapshotDTO],
        bookmaker_id_to_key_map: Optional[Dict[UUID, str]] = None,
    ) -> list[NormalizedOddsDTO]:
        """
        Aggregate OddsSnapshotDTO to NormalizedOddsDTO.

        Groups snapshots by event_id + market_type and calculates averages/bests.

        Args:
            snapshots: List of OddsSnapshotDTO
            bookmaker_id_to_key_map: Optional mapping from bookmaker_id to bookmaker_key for logging

        Returns:
            List of NormalizedOddsDTO (without id, created_at - will be set on persist)
        """
        logger.info(
            "aggregate_to_normalized_started",
            snapshots_count=len(snapshots)
        )

        if not snapshots:
            return []

        grouped: dict[tuple[UUID, str], list[OddsSnapshotDTO]] = defaultdict(list)
        for snapshot in snapshots:
            key = (snapshot.event_id, snapshot.market_type)
            grouped[key].append(snapshot)

        normalized_list: list[NormalizedOddsDTO] = []
        timestamp_ingested = now_utc()

        for (event_id, market_type), group_snapshots in grouped.items():
            home_odds: list[float] = []
            away_odds: list[float] = []
            draw_odds: list[float] = []
            bookmaker_ids: set[UUID] = set()
            latest_timestamp = timestamp_ingested

            for snapshot in group_snapshots:
                bookmaker_ids.add(snapshot.bookmaker_id)
                if snapshot.timestamp_source > latest_timestamp:
                    latest_timestamp = snapshot.timestamp_source

                for outcome in snapshot.outcomes:
                    if outcome.price <= 0:
                        continue

                    name_lower = outcome.name.lower() if outcome.name else ""

                    if outcome.role == "home" or (not outcome.role or outcome.role == "unknown"):
                        if "draw" in name_lower or name_lower == "draw":
                            draw_odds.append(outcome.price)
                        elif len(home_odds) == 0 or len(home_odds) <= len(away_odds):
                            home_odds.append(outcome.price)
                        else:
                            away_odds.append(outcome.price)
                    elif outcome.role == "away":
                        away_odds.append(outcome.price)
                    elif outcome.role == "draw":
                        draw_odds.append(outcome.price)
                    else:
                        if "draw" in name_lower or name_lower == "draw":
                            draw_odds.append(outcome.price)
                        elif len(home_odds) == 0:
                            home_odds.append(outcome.price)
                        else:
                            away_odds.append(outcome.price)

            # Calculate averages and best odds with proper rounding
            home_avg = safe_avg(home_odds)
            away_avg = safe_avg(away_odds)
            draw_avg = safe_avg(draw_odds, default=None)

            home_best = safe_best(home_odds)
            away_best = safe_best(away_odds)
            draw_best = safe_best(draw_odds, default=None)

            bookmakers_count = len(bookmaker_ids)

            # Build list of bookmaker keys for logging
            bookmaker_keys = []
            if bookmaker_id_to_key_map:
                for bookmaker_id in bookmaker_ids:
                    bookmaker_key = bookmaker_id_to_key_map.get(bookmaker_id)
                    if bookmaker_key:
                        bookmaker_keys.append(bookmaker_key)
            
            logger.debug(
                "aggregating_odds_group",
                event_id=str(event_id),
                market_type=market_type,
                bookmaker_keys=bookmaker_keys if bookmaker_keys else None,
                bookmaker_ids_count=bookmakers_count,
                snapshots_count=len(group_snapshots)
            )

            normalized = NormalizedOddsDTO(
                id=None,
                event_id=event_id,
                market_type=market_type,
                home_odds_avg=home_avg,
                away_odds_avg=away_avg,
                draw_odds_avg=draw_avg,
                home_odds_best=home_best,
                away_odds_best=away_best,
                draw_odds_best=draw_best,
                bookmakers_count=bookmakers_count,
                timestamp_source=latest_timestamp,
                timestamp_ingested=timestamp_ingested,
                timestamp_normalized=now_utc(),
                created_at=None,
            )
            normalized_list.append(normalized)

        logger.info(
            "aggregate_to_normalized_completed",
            normalized_count=len(normalized_list),
            events_processed=len(grouped)
        )

        return normalized_list

    async def get_upcoming_events_short(
        self,
        provider: str,
        provider_key: str,
    ) -> list[EventShortDTO]:
        """
        Get upcoming events as EventShortDTO for odds collection.

        Args:
            provider: Provider name
            provider_key: Competition provider key

        Returns:
            List of EventShortDTO
        """
        events = await self.events_cache.read_upcoming(provider_key)

        if events:
            return [
                EventShortDTO(
                    event_id=event.id,
                    external_id=event.external_id,
                )
                for event in events
            ]

        # Fallback to DB
        async with self.session_factory() as session:
            comp_repo = CompetitionsRepository(session)
            event_repo = EventRepository(session)

            competition = await comp_repo.get_by_provider_key(
                provider=provider,
                provider_key=provider_key
            )

            if not competition:
                return []

            events_orm = await event_repo.get_upcoming_by_competition(
                competition_id=competition.id,
                provider=provider
            )

            return [
                EventShortDTO(
                    event_id=event.id,
                    external_id=event.external_id,
                )
                for event in events_orm
            ]

    async def persist_competition_odds(
        self,
        competition_odds: CompetitionOddsDTO,
        provider: Optional[str] = None,
    ) -> dict[str, int]:
        """
        Persist competition odds to database (snapshots and normalized).

        Flow:
        1. Normalize CompetitionOddsDTO to snapshots
        2. In transaction:
           - Get/create bookmaker_id for each bookmaker
           - Upsert snapshots
           - Aggregate to normalized
           - Upsert normalized

        Args:
            competition_odds: CompetitionOddsDTO from fetch_odds_for_competition
            provider: Provider name (e.g., 'odds_api'). If not provided, will try to infer from policy.

        Returns:
            Dict with metrics: snapshots_inserted, snapshots_updated, normalized_inserted, normalized_updated
        """
        logger.info(
            "persist_competition_odds_started",
            provider_key=competition_odds.provider_key,
            events_count=len(competition_odds.events),
            provider=provider
        )

        # Get odds policy for filtering
        if not provider:
            # Try to get provider from policy (use first available)
            providers = self.policy_loader.get_providers()
            provider = providers[0] if providers else None
        
        if not provider:
            logger.warning(
                "provider_not_found_for_persist",
                provider_key=competition_odds.provider_key
            )
            return {
                "snapshots_inserted": 0,
                "snapshots_updated": 0,
                "normalized_inserted": 0,
                "normalized_updated": 0,
            }
        
        odds_policy = self.policy_loader.get_odds_policy(provider)
        
        snapshots = self.normalize_to_snapshots(competition_odds, odds_policy=odds_policy)
        if not snapshots:
            logger.info(
                "no_snapshots_to_persist",
                provider_key=competition_odds.provider_key
            )
            return {
                "snapshots_inserted": 0,
                "snapshots_updated": 0,
                "normalized_inserted": 0,
                "normalized_updated": 0,
            }

        snapshots_inserted = 0
        snapshots_updated = 0
        normalized_inserted = 0
        normalized_updated = 0

        # Build bookmaker_key_map from filtered snapshots (after policy filtering)
        # Map: (event_id, market_type, bookmaker_id) -> bookmaker_key
        # Note: We need to map from snapshot's temporary bookmaker_id to actual bookmaker_key
        # Since snapshots have temporary bookmaker.id from DTO, we need to find matching bookmaker_key
        # from competition_odds.events
        bookmaker_key_map: dict[tuple[UUID, str, UUID], str] = {}
        snapshot_id_to_key_map: dict[UUID, str] = {}
        
        # Build mapping from snapshot's temporary bookmaker.id to bookmaker.key
        for event_odds in competition_odds.events:
            for market_odds in event_odds.markets:
                if market_odds.bookmaker.key and market_odds.bookmaker.id:
                    # Map temporary bookmaker.id to bookmaker.key
                    snapshot_id_to_key_map[market_odds.bookmaker.id] = market_odds.bookmaker.key
                    # Also store by (event_id, market_type, bookmaker_id) for lookup
                    key = (event_odds.event_id, market_odds.market_type, market_odds.bookmaker.id)
                    bookmaker_key_map[key] = market_odds.bookmaker.key

        normalized: list[NormalizedOddsDTO] = []
        final_snapshots: list[OddsSnapshotDTO] = []

        async with self.session_factory() as session:
            async with session.begin():
                bookmaker_repo = BookmakerRepository(session)
                snapshot_repo = OddsSnapshotRepository(session)
                normalized_repo = NormalizedOddsRepository(session)

                bookmaker_cache: dict[str, UUID] = {}

                for snapshot in snapshots:
                    # Get bookmaker_key from snapshot's temporary bookmaker.id
                    bookmaker_key = snapshot_id_to_key_map.get(snapshot.bookmaker_id)

                    if not bookmaker_key:
                        logger.debug(
                            "bookmaker_key_not_found_for_snapshot",
                            event_id=str(snapshot.event_id),
                            market_type=snapshot.market_type
                        )
                        continue

                    if bookmaker_key not in bookmaker_cache:
                        bookmaker = await bookmaker_repo.get_by_key(bookmaker_key)
                        if not bookmaker:
                            for event_odds in competition_odds.events:
                                if event_odds.event_id == snapshot.event_id:
                                    for market_odds in event_odds.markets:
                                        if market_odds.bookmaker.key == bookmaker_key:
                                            bookmaker_id = await bookmaker_repo.get_or_create_by_key(
                                                key=bookmaker_key,
                                                name=market_odds.bookmaker.name,
                                                region=market_odds.bookmaker.region,
                                            )
                                            bookmaker_cache[bookmaker_key] = bookmaker_id
                                            break
                                    break
                        else:
                            bookmaker_cache[bookmaker_key] = bookmaker.id

                    if bookmaker_key not in bookmaker_cache:
                        logger.warning(
                            "failed_to_resolve_bookmaker",
                            bookmaker_key=bookmaker_key
                        )
                        continue

                    bookmaker_id = bookmaker_cache[bookmaker_key]

                    existing = await snapshot_repo.get_latest_by_event_and_bookmaker(
                        event_id=snapshot.event_id,
                        bookmaker_id=bookmaker_id,
                        market_type=snapshot.market_type
                    )

                    final_snapshot = OddsSnapshotDTO(
                        id=snapshot.id,
                        event_id=snapshot.event_id,
                        bookmaker_id=bookmaker_id,
                        market_type=snapshot.market_type,
                        outcomes=snapshot.outcomes,
                        timestamp_source=snapshot.timestamp_source,
                        timestamp_ingested=snapshot.timestamp_ingested,
                        created_at=snapshot.created_at,
                    )

                    await snapshot_repo.upsert_snapshot(final_snapshot)

                    if existing:
                        snapshots_updated += 1
                    else:
                        snapshots_inserted += 1

                    final_snapshots.append(final_snapshot)

                # Build bookmaker_id -> bookmaker_key mapping for logging
                # Use the bookmaker_cache which maps bookmaker_key -> bookmaker_id (UUID from DB)
                # and reverse it to get bookmaker_id -> bookmaker_key
                bookmaker_id_to_key_map: Dict[UUID, str] = {}
                for bookmaker_key, bookmaker_id in bookmaker_cache.items():
                    bookmaker_id_to_key_map[bookmaker_id] = bookmaker_key

                normalized = self.aggregate_to_normalized(final_snapshots, bookmaker_id_to_key_map=bookmaker_id_to_key_map)
                normalized_count = len(normalized)

                for norm_dto in normalized:
                    existing = await normalized_repo.get_latest_by_event(
                        event_id=norm_dto.event_id,
                        market_type=norm_dto.market_type
                    )

                    await normalized_repo.upsert_normalized(norm_dto)

                    if existing:
                        normalized_updated += 1
                    else:
                        normalized_inserted += 1

        logger.info(
            "persist_competition_odds_completed",
            competition_key=competition_odds.provider_key,
            snapshots_inserted=snapshots_inserted,
            snapshots_updated=snapshots_updated,
            normalized_inserted=normalized_inserted,
            normalized_updated=normalized_updated,
        )

        logger.debug(
            "persist_competition_odds_details",
            competition_key=competition_odds.provider_key,
            events_count=len(competition_odds.events),
            snapshots_count=len(final_snapshots),
            normalized_count=len(normalized),
        )

        event_odds_map: dict[UUID, list[NormalizedOddsDTO]] = {}
        for norm_dto in normalized:
            if norm_dto.event_id not in event_odds_map:
                event_odds_map[norm_dto.event_id] = []
            event_odds_map[norm_dto.event_id].append(norm_dto)

        for event_id, items in event_odds_map.items():
            await self.odds_cache.write_event_odds_atomic(
                provider_key=competition_odds.provider_key,
                event_id=event_id,
                items=items,
                ttl_sec=None
            )

        return {
            "snapshots_inserted": snapshots_inserted,
            "snapshots_updated": snapshots_updated,
            "normalized_inserted": normalized_inserted,
            "normalized_updated": normalized_updated,
        }

    async def get_event_odds(
        self,
        provider_key: str,
        event_id: UUID,
    ) -> list[NormalizedOddsDTO]:
        """
        Get normalized odds for an event (read-through cache).

        Flow:
        1. Try to read from cache
        2. If cache hit (non-empty) → return
        3. If cache miss:
           - Get from DB
           - If found → warm cache and return
           - If not found → return empty list + log

        Args:
            provider_key: Competition provider_key
            event_id: Event UUID

        Returns:
            List of NormalizedOddsDTO (empty if not found)
        """
        cached = await self.odds_cache.read_event_odds(
            provider_key=provider_key,
            event_id=event_id
        )

        if cached:
            return cached

        async with self.session_factory() as session:
            normalized_repo = NormalizedOddsRepository(session)
            normalized_list = await normalized_repo.get_by_event(
                event_id=event_id,
                market_type=None
            )

            if normalized_list:
                items = [
                    NormalizedOddsDTO(
                        id=norm.id,
                        event_id=norm.event_id,
                        market_type=norm.market_type,
                        home_odds_avg=norm.home_odds_avg,
                        away_odds_avg=norm.away_odds_avg,
                        draw_odds_avg=norm.draw_odds_avg,
                        home_odds_best=norm.home_odds_best,
                        away_odds_best=norm.away_odds_best,
                        draw_odds_best=norm.draw_odds_best,
                        bookmakers_count=norm.bookmakers_count,
                        timestamp_source=norm.timestamp_source,
                        timestamp_ingested=norm.timestamp_ingested,
                        timestamp_normalized=norm.timestamp_normalized,
                        created_at=norm.created_at,
                    )
                    for norm in normalized_list
                ]

                await self.odds_cache.write_event_odds_atomic(
                    provider_key=provider_key,
                    event_id=event_id,
                    items=items,
                    ttl_sec=None
                )

                return items

        logger.info(
            "normalized_odds_not_found",
            provider_key=provider_key,
            event_id=str(event_id)
        )

        return []


