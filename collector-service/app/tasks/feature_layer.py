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
    """Collect team features from standings for configured competitions."""
    start_time = now_utc()
    logger.info("collect_team_features_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    provider = "odds_api"
    total_saved = 0
    total_errors = 0

    try:
        builder = await get_collect_team_features_builder()
        container = broker.state.container
        policy_loader = container.policy_loader
        catalog_helper = builder.catalog_cache_helper

        api_football_policy = policy_loader.get_api_football(provider)
        if not api_football_policy or not api_football_policy.competitions:
            logger.warning("no_api_football_policy_found", provider=provider)
            return {
                "status": "ok",
                "saved": str(total_saved),
                "errors": str(total_errors)
            }

        for slug_key, comp_config in api_football_policy.competitions.items():
            try:
                seasons_current = comp_config.seasons.current

                competitions = await catalog_helper.get_competitions_by_slugs("soccer", [slug_key])
                if not competitions:
                    logger.warning("competition_not_found", slug_key=slug_key)
                    total_errors += 1
                    continue

                competition = competitions[0]
                competition_id = competition.id

                rows = await builder.load_standings_rows(competition_id, seasons_current)
                if not rows:
                    logger.info("no_standings_rows", slug_key=slug_key, competition_id=str(competition_id), season=seasons_current)
                    continue

                features = await builder.features_from_standings(rows, competition_id, seasons_current)
                if not features:
                    logger.info("no_features_built", slug_key=slug_key, competition_id=str(competition_id), season=seasons_current)
                    continue

                count = await builder.save_team_features(features, competition_id, seasons_current)
                total_saved += count

                logger.info(
                    "team_features_saved",
                    competition_id=str(competition_id),
                    season=seasons_current,
                    count=count
                )

            except Exception as exc:
                logger.error(
                    "team_features_collect_failed",
                    slug_key=slug_key,
                    error=str(exc),
                    exc_info=True
                )
                total_errors += 1

        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)

        logger.info(
            "collect_team_features_task_completed",
            duration_seconds=duration,
            saved=total_saved,
            errors=total_errors
        )

        return {
            "status": "ok",
            "saved": str(total_saved),
            "errors": str(total_errors)
        }

    except Exception as e:
        logger.error("collect_team_features_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}

