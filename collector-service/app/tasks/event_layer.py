from typing import Dict, TYPE_CHECKING

import structlog
from prometheus_client import Counter, Histogram

from app.tasks.broker import broker
from app.utils.time_utils import now_utc
from app.infrastructure.di.services import get_collect_team_features_service, get_event_layer_service, get_layer_model_service, get_odds_service

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

collection_duration = Histogram("event_layer_collection_duration_seconds", "Time spent building event layer")
events_processed_total = Counter("event_layer_events_processed_total", "Total number of event layer events processed")
collection_errors_total = Counter("event_layer_collection_errors_total", "Total number of collection errors")

#
# _task_schedule = [{"cron": cron} for cron in settings.schedule_crons]
# _sports_task_schedule = [{"cron": cron} for cron in settings.schedule_sports_crons]


@broker.task()
async def collect_event_feature_bundle_task() -> Dict[str, str]:
    """Collect event feature bundle from fixtures."""
    logger.debug("collect_event_feature_bundle_task_started")

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    container = broker.state.container
    provider = "odds_api"
    total_processed = 0

    try:

        service_team_features = await get_collect_team_features_service()
        service_layer_models = await get_layer_model_service()
        service_event_layer = await get_event_layer_service()
        service_odds = await get_odds_service()
        policy_loader = container.policy_loader
        catalog_helper = service_team_features.catalog_cache_helper

        api_football_policy = policy_loader.get_api_football(provider)
        if not api_football_policy or not api_football_policy.competitions:
            logger.warning("no_api_football_policy_found", provider=provider)
            return {
                "status": "ok",
                "processed": "0"
            }

        for slug_key, comp_config in api_football_policy.competitions.items():
            competition_id = None
            try:
                seasons_current = comp_config.seasons.current

                competitions = await catalog_helper.get_competitions_by_slugs("soccer", [slug_key])
                if not competitions:
                    logger.warning("competition_not_found", slug_key=slug_key)
                    continue

                competition = competitions[0]
                competition_id = competition.id

                logger.debug(
                    "event_feature_bundle_competition_processing",
                    competition_id=str(competition_id),
                    season=seasons_current
                )

                events, team_ids = await service_team_features.get_events_by_competition(
                    competition_id,
                    seasons_current
                )
                if not events:
                    logger.debug("no_events_found", competition_id=str(competition_id), season=seasons_current)
                    continue

                logger.debug("event_feature_bundle_events_loaded", count=len(events))

                odds_events = await service_odds.get_normalized_odds_by_events(slug_key=slug_key, fixtures=events)

                if not odds_events:
                    logger.debug("no_features_extracted", competition_id=str(competition_id), season=seasons_current)
                    continue

                outputs = service_layer_models.poisson_model_builder.build_for_fixtures(features)
                logger.debug("poisson_models_built", count=len(outputs))

                if not outputs:
                    continue

                await service_layer_models.save_poisson_model(
                    outputs=outputs,
                    competition_id=competition_id,
                    season=seasons_current,
                )
                total_processed += len(outputs)

                logger.debug("event_feature_bundle_models_saved", count=len(outputs))

            except Exception as exc:
                logger.error(
                    "event_feature_bundle_collect_failed",
                    slug_key=slug_key,
                    competition_id=str(competition_id) if competition_id else None,
                    error=str(exc),
                    exc_info=True
                )

        return {
            "status": "ok",
            "processed": str(total_processed)
        }
    except Exception as e:
        logger.error("event_feature_bundle_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}