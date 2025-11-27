from typing import Dict, TYPE_CHECKING

import structlog
from prometheus_client import Counter, Histogram

from app.tasks.broker import broker
from app.utils.time_utils import now_utc
from app.infrastructure.di.services import get_collect_team_features_service, get_layer_model_service

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

collection_duration = Histogram("models_layer_collection_duration_seconds", "Time spent building models layer")
events_processed_total = Counter("models_layer_events_processed_total", "Total number of models layer events processed")
collection_errors_total = Counter("models_layer_collection_errors_total", "Total number of collection errors")

#
# _task_schedule = [{"cron": cron} for cron in settings.schedule_crons]
# _sports_task_schedule = [{"cron": cron} for cron in settings.schedule_sports_crons]


@broker.task()
async def collect_layer_models_elo_task() -> Dict[str, str]:
    """Collect Elo model from fixtures """
    start_time = now_utc()
    logger.info("collect_models_elo_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    provider = "odds_api"
    total_saved = 0
    total_errors = 0

    try:
        service_team_features = await get_collect_team_features_service()
        service_layer_models = await get_layer_model_service()
        container = broker.state.container
        policy_loader = container.policy_loader
        catalog_helper = service_team_features.catalog_cache_helper

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

                logger.info(
                    "collect_models_elo_task_started",
                    competition_id=str(competition_id),
                    season=seasons_current,
                    slug_key=slug_key
                )

                events, team_ids = await service_team_features.get_events_by_competition(competition_id, seasons_current)
                if not events:
                    logger.info("no_events_found", slug_key=slug_key, competition_id=str(competition_id), season=seasons_current)
                    continue

                logger.info(
                    "events_fetched",
                    competition_id=str(competition_id),
                    season=seasons_current,
                    slug_key=slug_key,
                    events_count=len(events)
                )

                features = await service_layer_models.extract_features_for_elo_build(events, team_ids, competition_id, seasons_current)
                if not features:
                    logger.info("no_fixtures_rows", slug_key=slug_key, competition_id=str(competition_id), season=seasons_current)
                    continue


                input_features = service_layer_models.elo_model_builder.build_for_fixtures(features)
                logger.info(
                    "fixtures_fetched",
                    competition_id=str(competition_id),
                    season=seasons_current,
                    slug_key=slug_key,
                    fixtures_count=len(input_features)
                )

                logger.info("saving_elo_model", count=len(input_features))
                count = await service_layer_models.save_elo_model(input_features, competition_id, seasons_current)
                total_saved += count

                logger.info(
                    "elo_model_saved",
                    competition_id=str(competition_id),
                    season=seasons_current,
                    count=count
                )

            except Exception as exc:
                logger.error(
                    "elo_model_collect_failed",
                    slug_key=slug_key,
                    error=str(exc),
                    exc_info=True
                )
                total_errors += 1
        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)

        logger.info(
            "elo_model_task_completed",
            duration_seconds=duration,
            errors=total_errors,
            saved_count=total_saved
        )

        return {
            "status": "ok",
            "saved": str(total_saved),
            "errors": str(total_errors)
        }
    except Exception as e:
        logger.error("elo_model_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}