from typing import Dict, TYPE_CHECKING
import structlog
from prometheus_client import Counter, Histogram

from app.config import settings
from app.utils.time_utils import now_utc, build_events_window
from app.infrastructure.di.services import get_sports_service, get_events_service, get_odds_service, \
    get_collect_statistic_sync_service, get_collect_team_features_builder
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.tasks.broker import broker
from app.domain.entities.events.events_window import EventsWindowDTO
from app.tasks.prioritizer import enqueue_prioritization_after_collect

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

collection_duration = Histogram("feature_layer_collection_duration_seconds", "Time spent building feature layer")
events_processed_total = Counter("feature_layer_events_processed_total", "Total number of team features events processed")
collection_errors_total = Counter("feature_layer_collection_errors_total", "Total number of collection errors")

#
# _task_schedule = [{"cron": cron} for cron in settings.schedule_crons]
# _sports_task_schedule = [{"cron": cron} for cron in settings.schedule_sports_crons]


@broker.task()
async def collect_team_features_task() -> Dict[str, str]:
    start_time = now_utc()
    logger.info("collect_team_features_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    provider = "odds_api"
    total_processed = 0
    total_errors = 0

    try:
        service = await get_collect_team_features_builder()
        container = broker.state.container
        policy_loader = container.policy_loader
        standings_cache = service.standings_cache

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

