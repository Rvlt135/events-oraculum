from typing import Dict, TYPE_CHECKING
import structlog
from prometheus_client import Counter, Histogram

from app.config import settings
from app.utils.time_utils import now_utc, build_events_window
from app.infrastructure.di.services import get_sports_service, get_events_service, get_odds_service
from app.tasks.broker import broker
from app.domain.entities.events.events_window import EventsWindowDTO
from app.tasks.prioritizer import enqueue_prioritization_after_collect

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

collection_duration = Histogram("odds_collection_duration_seconds", "Time spent collecting odds data")
events_processed_total = Counter("odds_events_processed_total", "Total number of events processed")
collection_errors_total = Counter("odds_collection_errors_total", "Total number of collection errors")


_task_schedule = [{"cron": cron} for cron in settings.schedule_crons]
_sports_task_schedule = [{"cron": cron} for cron in settings.schedule_sports_crons]

@broker.task(schedule=_sports_task_schedule)
async def collect_sports_task() -> Dict[str, str]:
    """
    Collect and sync sports data from external provider.
    
    This task is now thin and delegates to SportsService.
    """
    start_time = now_utc()

    try:
        # Get sports service - it manages its own session lifecycle
        sports_service = await get_sports_service()
        
        # Delegate to service for business logic
        result = await sports_service.sync_sports_and_competitions()
        
        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)
        
        logger.info(
            "sports_collection_task_completed",
            duration_seconds=duration,
            **result
        )
        
        # Handle new nested result structure
        categories_count = result.get("categories", {}).get("synced_count", 0)
        competitions_count = result.get("competitions", {}).get("synced_count", 0)
        
        return {
            "status": result["status"],
            "categories_synced": str(categories_count),
            "competitions_synced": str(competitions_count),
            "timestamp": now_utc().isoformat(),
        }

    except Exception as e:
        logger.error("sports_collection_task_failed", error=str(e))
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}

@broker.task()
async def collect_events() -> Dict[str, str]:
    """
    Collect events for all active competitions from provider (E10).

    No runtime parameters - all configuration from provider_policy.yml:
    - Competition list with plan_visibility and is_active filtering
    - Time window from events_window.period
    - Rate limits and retry policy from events_window
    - Cache TTL from events_cache.upcoming_ttl_sec

    Returns summary with inserted/updated/skipped counts and errors.
    """
    start_time = now_utc()
    logger.info("collect_events_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    try:
        # Get EventsService from DI
        events_service = await get_events_service()

        # Get policy loader from container
        container = broker.state.container
        policy_loader = container.policy_loader

        # Get providers from policy
        providers = policy_loader.get_providers()
        if not providers:
            logger.warning("no_providers_found_in_policy")
            return {
                "status": "error",
                "message": "No providers found in policy",
                "timestamp": now_utc().isoformat(),
            }

        # For now, process first provider (can be extended to support multiple providers)
        provider = providers[0]
        logger.info("provider_selected_from_policy", provider=provider, total_providers=len(providers))

        # Load policy for selected provider
        policy = policy_loader.get_events_policy(provider)
        if not policy:
            logger.warning("policy_not_found_for_provider", provider=provider)
            return {
                "status": "error",
                "message": f"Policy not found for provider: {provider}",
                "timestamp": now_utc().isoformat(),
            }

        # Get competitions from policy using DTO
        competitions_free = policy.competitions.get("free", [])
        competitions_pro = policy.competitions.get("pro", [])
        all_competition_keys = list(set(competitions_free + competitions_pro))

        logger.info(
            "collect_events_policy_loaded",
            provider=provider,
            total_competitions=len(all_competition_keys),
            free_count=len(competitions_free),
            pro_count=len(competitions_pro)
        )

        # Filter active competitions using cache-first with DB fallback
        active_keys = []
        for key in all_competition_keys:
            category = key.split("_")[0] if "_" in key else "unknown"
            is_active = await events_service.check_competition_active(
                category=category,
                slug_key=key,
                provider=provider
            )
            if is_active:
                active_keys.append(key)
            else:
                logger.info("competition_filtered_inactive", slug_key=key)

        logger.info("active_competitions_filtered", total=len(all_competition_keys), active=len(active_keys))

        if not active_keys:
            logger.warning("no_active_competitions_found")
            return {
                "status": "success",
                "message": "No active competitions to process",
                "timestamp": now_utc().isoformat(),
            }

        # Build time window from policy using DTO
        period_days = policy.period
        commence_time_from, commence_time_to = build_events_window(period_days)

        window = EventsWindowDTO(
            from_iso=commence_time_from,
            to_iso=commence_time_to,
            period_days=period_days
        )

        logger.info(
            "events_window_built",
            period_days=period_days,
            from_iso=window.from_iso,
            to_iso=window.to_iso
        )
        summary = await events_service.process_events_and_competitions(
            provider=provider,
            policy=policy,
            keys=active_keys,
            window=window
        )
        # Process competitions


        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)

        logger.info(
            "collect_events_task_completed",
            duration_seconds=duration,
            processed=summary.processed,
            failed=summary.failed,
            skipped=summary.skipped,
            total_events=summary.total_events
        )

        result = {
            "status": "success",
            "processed": str(summary.processed),
            "failed": str(summary.failed),
            "skipped": str(summary.skipped),
            "total_events": str(summary.total_events),
            "duration_seconds": str(duration),
            "timestamp": now_utc().isoformat(),
        }
        # TODO:DEBUG: disable prioritization
        # await enqueue_prioritization_after_collect(result)

        return result

    except Exception as e:
        logger.error("collect_events_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}


@broker.task(schedule=_task_schedule)
async def collect_odds_task() -> Dict[str, str]:
    """
    Collect odds for competitions with upcoming events from provider.

    Configuration from provider_policy.yml:
    - Competition list from events_policy.competitions (free + pro)
    - Time window from events_window.period
    - Odds settings from odds_policy (regions, markets, bookmakers, etc.)
    """
    start_time = now_utc()
    logger.info("collect_odds_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    try:
        odds_service = await get_odds_service()
        container = broker.state.container
        policy_loader = container.policy_loader

        # Get providers from policy
        providers = policy_loader.get_providers()
        if not providers:
            logger.warning("no_providers_found_in_policy")
            return {
                "status": "error",
                "message": "No providers found in policy",
                "timestamp": now_utc().isoformat(),
            }

        provider = providers[0]
        logger.info("provider_selected_from_policy", provider=provider, total_providers=len(providers))

        # Load policies for selected provider
        events_policy = policy_loader.get_events_policy(provider)
        odds_policy = policy_loader.get_odds_policy(provider)

        if not events_policy:
            logger.warning("events_policy_not_found_for_provider", provider=provider)
            return {
                "status": "error",
                "message": f"Events policy not found for provider: {provider}",
                "timestamp": now_utc().isoformat(),
            }

        if not odds_policy:
            logger.warning("odds_policy_not_found_for_provider", provider=provider)
            return {
                "status": "error",
                "message": f"Odds policy not found for provider: {provider}",
                "timestamp": now_utc().isoformat(),
            }

        # Get competitions from policy using DTO
        competitions_free = events_policy.competitions.get("free", [])
        competitions_pro = events_policy.competitions.get("pro", [])
        all_competition_keys = list(set(competitions_free + competitions_pro))

        logger.info(
            "collect_odds_policy_loaded",
            provider=provider,
            total_competitions=len(all_competition_keys),
            free_count=len(competitions_free),
            pro_count=len(competitions_pro)
        )

        # Build time window from policy using DTO
        period_days = events_policy.period
        commence_time_from, commence_time_to = build_events_window(period_days)

        window = EventsWindowDTO(
            from_iso=commence_time_from,
            to_iso=commence_time_to,
            period_days=period_days
        )

        logger.info(
            "odds_window_built",
            period_days=period_days,
            from_iso=window.from_iso,
            to_iso=window.to_iso
        )

        # Get competitions with actual upcoming events
        keys_for_odds = await odds_service.get_competitions_for_odds(
            provider=provider
        )

        if not keys_for_odds:
            logger.warning("no_competitions_with_upcoming_events")
            return {
                "status": "success",
                "message": "No competitions with upcoming events to process",
                "timestamp": now_utc().isoformat(),
            }

        logger.info(
            "competitions_selected_for_odds",
            total=len(keys_for_odds),
            keys=keys_for_odds
        )

        # Process odds collection for selected competitions
        total_events_count = 0
        total_events_with_odds = 0
        total_snapshots_written = 0
        total_normalized_written = 0
        total_missing_odds = 0
        total_orphan_odds = 0

        for competition_key in keys_for_odds:
            # Get upcoming events as EventShortDTO
            upcoming_events = await odds_service.get_upcoming_events_short(
                provider=provider,
                slug_key=competition_key,
            )

            if not upcoming_events:
                continue

            events_count = len(upcoming_events)
            total_events_count += events_count

            # Fetch odds using new service method
            competition_odds = await odds_service.fetch_odds_for_competition(
                provider=provider,
                slug_key=competition_key,
                upcoming_events=upcoming_events,
            )

            events_with_odds = len(competition_odds.events)
            missing_odds = events_count - events_with_odds
            total_events_with_odds += events_with_odds
            total_missing_odds += missing_odds

            if not competition_odds.events:
                logger.info(
                    "odds_collect_summary",
                    slug_key=competition_key,
                    events_count=events_count,
                    events_with_odds=0,
                    snapshots_written=0,
                    normalized_written=0,
                    missing_odds=missing_odds,
                    orphan_odds=0
                )
                continue

            # Persist odds (normalize + write to DB + cache)
            metrics = await odds_service.persist_competition_odds(
                competition_odds,
                provider=provider,
                odds_policy=odds_policy
            )
            snapshots_written = metrics["snapshots_inserted"] + metrics["snapshots_updated"]
            normalized_written = metrics["normalized_inserted"] + metrics["normalized_updated"]
            total_snapshots_written += snapshots_written
            total_normalized_written += normalized_written

            event_ids_with_odds = {e.event_id for e in competition_odds.events}
            orphan_odds = 0
            for event_odds in competition_odds.events:
                if not event_odds.markets:
                    orphan_odds += 1
            total_orphan_odds += orphan_odds

            logger.info(
                "odds_collect_summary",
                slug_key=competition_key,
                events_count=events_count,
                events_with_odds=events_with_odds,
                snapshots_written=snapshots_written,
                normalized_written=normalized_written,
                missing_odds=missing_odds,
                orphan_odds=orphan_odds
            )

        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)

        logger.info(
            "odds_collect_task_completed",
            duration_seconds=duration,
            total_events_count=total_events_count,
            total_events_with_odds=total_events_with_odds,
            total_snapshots_written=total_snapshots_written,
            total_normalized_written=total_normalized_written,
            total_missing_odds=total_missing_odds,
            total_orphan_odds=total_orphan_odds,
            competitions_processed=len(keys_for_odds)
        )

        return {
            "status": "success",
            "total_events_count": str(total_events_count),
            "total_events_with_odds": str(total_events_with_odds),
            "total_snapshots_written": str(total_snapshots_written),
            "total_normalized_written": str(total_normalized_written),
            "total_missing_odds": str(total_missing_odds),
            "total_orphan_odds": str(total_orphan_odds),
            "competitions_processed": str(len(keys_for_odds)),
            "duration_seconds": str(duration),
            "timestamp": now_utc().isoformat(),
        }

    except Exception as e:
        logger.error("collect_odds_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}
