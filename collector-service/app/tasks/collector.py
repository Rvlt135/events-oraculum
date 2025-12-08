from typing import Dict, TYPE_CHECKING
import structlog
from prometheus_client import Counter, Histogram

from app.config import settings
from app.infrastructure.di.container import Container
from app.infrastructure.di.factory import create_sports_service, create_events_service, create_odds_service, \
    create_statistics_collect_service
from app.utils.time_utils import now_utc, build_events_window
from app.infrastructure.repositories.competitions import CompetitionsRepository
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
        container: "Container" = broker.state.container

        sports_service = create_sports_service(container)
        
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
        container: "Container" = broker.state.container
        events_service = create_events_service(container)

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
        api_football_policy = policy_loader.get_api_football(provider)
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
        await enqueue_prioritization_after_collect(result)

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
        container = broker.state.container
        odds_service = create_odds_service(container)
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


@broker.task()
async def collect_standings_football_task() -> Dict[str, str]:
    start_time = now_utc()
    logger.info("collect_standings_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    provider = "odds_api"
    total_processed = 0
    total_errors = 0

    try:
        container = broker.state.container
        service = create_statistics_collect_service(container)
        policy_loader = container.policy_loader
        catalog_helper = service.catalog_cache_helper

        api_football_policy = policy_loader.get_api_football(provider)
        if not api_football_policy or not api_football_policy.competitions:
            logger.warning("no_api_football_policy_found", provider=provider)
            return {
                "status": "ok",
                "processed": str(total_processed),
                "errors": str(total_errors)
            }

        for slug_key, comp_config in api_football_policy.competitions.items():
            try:
                league_id = comp_config.league_id
                seasons_list = [comp_config.seasons.current]
                if comp_config.seasons.previous:
                    seasons_list.append(comp_config.seasons.previous)

                competitions = await catalog_helper.get_competitions_by_slugs("soccer", [slug_key]) # TODO: update dynamic category sport??
                if not competitions:
                    logger.warning("competition_not_found", slug_key=slug_key)
                    total_errors += 1
                    continue

                competition = competitions[0]
                sport_id = competition.sport_id
                competition_id = competition.id

                for season in seasons_list:
                    try:
                        prepared = await service.fetch_and_prepare_standings(league_id, season)
                        if not prepared.api_team_ids:
                            logger.info("no_teams_in_standings", slug_key=slug_key, league_id=league_id, season=season)
                            continue

                        team_map = await service.resolve_teams_for_standings(prepared, sport_id)
                        records = service.build_standing_records(prepared, team_map, competition_id, season)
                        
                        if not records:
                            logger.info("no_records_built", slug_key=slug_key, league_id=league_id, season=season)
                            continue

                        count = await service.save_standings(records, slug_key, season)
                        total_processed += 1

                        # records_dict = service._to_cache_items(records)
                        # await service.standings_football_cache.save_standings_teams(str(league_id), season, records_dict)

                        logger.info(
                            "standings_saved",
                            slug_key=slug_key,
                            league_id=league_id,
                            season=season,
                            count=count
                        )
                    except Exception as e:
                        logger.error(
                            "standings_season_error",
                            slug_key=slug_key,
                            league_id=league_id,
                            season=season,
                            error=str(e),
                            exc_info=True
                        )
                        total_errors += 1

            except Exception as e:
                logger.error(
                    "standings_slug_error",
                    slug_key=slug_key,
                    error=str(e),
                    exc_info=True
                )
                total_errors += 1

        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)

        logger.info(
            "collect_standings_task_completed",
            duration_seconds=duration,
            processed=total_processed,
            errors=total_errors
        )

        return {
            "status": "ok",
            "processed": str(total_processed),
            "errors": str(total_errors)
        }

    except Exception as e:
        logger.error("collect_standings_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}


@broker.task()
async def collect_fixtures_football_task() -> Dict[str, str]:
    start_time = now_utc()
    logger.info("collect_fixtures_football_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    provider = "odds_api"
    total_processed = 0
    total_errors = 0

    try:

        container = broker.state.container
        service = create_statistics_collect_service(container)
        policy_loader = container.policy_loader
        catalog_helper = service.catalog_cache_helper

        api_football_policy = policy_loader.get_api_football(provider)
        if not api_football_policy or not api_football_policy.competitions:
            logger.warning("no_api_football_policy_found", provider=provider)
            return {
                "status": "ok",
                "processed": str(total_processed),
                "errors": str(total_errors)
            }

        for slug_key, comp_config in api_football_policy.competitions.items():
            # TODO: refactoring to methods prepare data.
            try:
                league_id = comp_config.league_id
                seasons_current = comp_config.seasons.current

                competitions = await catalog_helper.get_competitions_by_slugs("soccer",
                                                                              [slug_key])  # TODO: update dynamic category sport??
                if not competitions:
                    logger.warning("competition_not_found", slug_key=slug_key)
                    total_errors += 1
                    continue

                competition = competitions[0]
                sport_id = competition.sport_id
                competition_id = competition.id

                response = await service.api_football_client.get_fixtures(league_id, seasons_current)

                prepared = await service.filter_and_prepare_fixtures(response)
                if not prepared.api_team_ids:
                    logger.info("no_teams_in_standings", slug_key=slug_key, league_id=league_id, season=seasons_current)
                    continue

                team_map = await service.resolve_teams_for_fixtures(prepared, sport_id)
                records = service.build_fixture_records(prepared, team_map, competition_id, seasons_current)

                if not records:
                    logger.info("no_records_built", slug_key=slug_key, league_id=league_id, season=seasons_current)
                    continue

                count = await service.save_fixtures(records, slug_key, seasons_current)
                total_processed += 1

                logger.info(
                    "collect_fixtures_saved",
                    slug_key=slug_key,
                    league_id=league_id,
                    season=seasons_current,
                    count=count
                )

            except Exception as e:
                logger.error(
                    "collect_fixtures_slug_error",
                    slug_key=slug_key,
                    error=str(e),
                    exc_info=True
                )
                total_errors += 1

        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)

        logger.info(
            "collect_fixtures_football_task_completed",
            duration_seconds=duration,
            processed=total_processed,
            errors=total_errors
        )

        return {
            "status": "ok",
            "processed": str(total_processed),
            "errors": str(total_errors)
        }

    except Exception as e:
        logger.error("collect_fixtures_football_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}


