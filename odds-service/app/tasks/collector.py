from typing import Dict, TYPE_CHECKING
import structlog
from prometheus_client import Counter, Histogram

from app.config import settings
from app.infrastructure.repositories import SportRepository, CompetitionsRepository
from app.utils.time_utils import now_utc, build_events_window
from app.infrastructure.di.services import get_sports_service, get_events_service, get_odds_service
from app.tasks.broker import broker
from app.domain.entities.events_window import EventsWindowDTO, EventsPolicyDTO
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
                provider_key=key,
                provider=provider
            )
            if is_active:
                active_keys.append(key)
            else:
                logger.info("competition_filtered_inactive", provider_key=key)

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
        await enqueue_prioritization_after_collect(result)

        return result

    except Exception as e:
        logger.error("collect_events_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}


# @broker.task(schedule=_task_schedule)
# async def collect_odds_task() -> Dict[str, str]:
#     start_time = now_utc()
#     logger.info("collection_task_started", timestamp=start_time.isoformat(), schedule=_task_schedule)
#
#     # Get container from broker state
#     if not hasattr(broker.state, 'container'):
#         raise RuntimeError("Container not found in broker.state. Make sure worker/scheduler initialized container.")
#
#     odds_service = await get_odds_service()
#     container = broker.state.container
#     policy_loader = container.policy_loader
#
#     # Get providers from policy
#     providers = policy_loader.get_providers()
#     provider_odds_api = providers[0]
#     pl: EventsPolicyDTO = policy_loader.get_events_policy(provider_odds_api)
#     if not providers:
#         logger.warning("no_providers_found_in_policy")
#         return {
#             "status": "error",
#             "message": "No providers found in policy",
#             "timestamp": now_utc().isoformat(),
#         }
#
#     try:
#
#         # Use session factory from container
#         async with container.session_factory() as session:
#             async with session.begin():
#                 sport_repo = SportRepository(session)
#                 competition_repo = CompetitionsRepository(session)
#
#                 sport_id = await sport_repo.get_or_create("soccer", provider=provider_odds_api)
#
#                 # Get events window period from policy and build time window
#
#                 commence_time_from, commence_time_to = build_events_window(pl.period)
#                 logger.info(
#                     "events_window_configured",
#                     period_days=pl.period,
#                     commence_time_from=commence_time_from,
#                     commence_time_to=commence_time_to
#                 )
#
#                 total_processed = 0
#
#                 for competition_key in settings.odds_api_competitions:
#                     logger.info("collecting_competition", competition=competition_key)
#
#                     competition_id = await competition_repo.get_or_create(
#                         sport_id=sport_id,
#                         provider_key=competition_key,
#                         title=competition_key.replace("_", " ").title(),
#                         description=f"Competition for {competition_key}",
#                     )
#
#                     odds_data = await odds_service.odds_client.get_odds(
#                         sport=competition_key,
#                         regions=settings.odds_api_regions,
#                         markets=settings.odds_api_markets,
#                         commence_time_from=commence_time_from,
#                         commence_time_to=commence_time_to,
#                     )
#
#                     events_processed = 0
#                     for event_data in odds_data:
#                         event_id = await odds_service.process_event_data(event_data, sport_id, competition_id)
#                         if event_id:
#                             events_processed += 1
#
#                     logger.info("competition_processed", competition=competition_key, events_count=events_processed)
#                     events_processed_total.inc(events_processed)
#                     total_processed += events_processed
#
#         duration = (now_utc() - start_time).total_seconds()
#         collection_duration.observe(duration)
#
#         logger.info(
#             "collection_task_completed",
#             total_events=total_processed,
#             duration_seconds=duration,
#         )
#
#         return {
#             "status": "success",
#             "total_events": str(total_processed),
#             "timestamp": now_utc().isoformat(),
#         }
#
#     except Exception as e:
#         logger.error("collection_task_failed", error=str(e))
#         collection_errors_total.inc()
#         return {"status": "error", "message": str(e)}
#
#     # Note: api_adapter (odds_client) lifecycle is managed by container
#     # No need to close it here - it will be closed in dispose_container()
