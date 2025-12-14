from typing import Dict, TYPE_CHECKING

import structlog
from prometheus_client import Counter, Histogram

from app.infrastructure.di.container import Container
from app.infrastructure.di.factory import create_team_features_service, create_layer_model_service, \
    create_event_layer_service, create_odds_service
from app.tasks.broker import broker

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

collection_duration = Histogram("event_layer_collection_duration_seconds", "Time spent building event layer")
events_processed_total = Counter("event_layer_events_processed_total", "Total number of event layer events processed")
collection_errors_total = Counter("event_layer_collection_errors_total", "Total number of collection errors")


@broker.task()
async def collect_event_feature_bundles_task() -> Dict[str, str]:
    """Collect event feature bundles from fixtures and persist enriched bundles."""
    logger.debug("collect_event_feature_bundles_task_started")

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    container: "Container" = broker.state.container
    provider = "odds_api"

    try:
        # Resolve services via DI
        service_team_features = create_team_features_service(container)
        service_layer_models = create_layer_model_service(container)
        service_event_layer = create_event_layer_service(container)
        service_odds = create_odds_service(container)
        
        policy_loader = container.policy_loader
        catalog_helper = service_team_features.catalog_cache_helper

        api_football_policy = policy_loader.get_api_football(provider)
        if not api_football_policy or not api_football_policy.competitions:
            logger.warning("no_api_football_policy_found", provider=provider)
            return {"status": "ok", "processed": "0"}

        last_result = None
        for slug_key, comp_config in api_football_policy.competitions.items():
            competition_id = None
            try:
                season = comp_config.seasons.current

                competitions = await catalog_helper.get_competitions_by_slugs("soccer", [slug_key])
                if not competitions:
                    logger.warning("competition_not_found", slug_key=slug_key)
                    continue

                competition = competitions[0]
                competition_id = competition.id

                logger.debug(
                    "event_feature_bundle_competition_processing",
                    competition_id=str(competition_id),
                    season=season,
                    slug_key=slug_key,
                )

                # Load fixtures
                fixtures, team_ids_set = await service_team_features.get_events_by_competition(
                    competition_id,
                    season,
                )
                if not fixtures:
                    logger.debug("no_fixtures_found", competition_id=str(competition_id), season=season)
                    last_result = {"status": "no-fixtures"}
                    continue

                logger.debug("fixtures_loaded", count=len(fixtures), competition_id=str(competition_id), season=season)

                # Load normalized odds
                odds_map = await service_odds.get_normalized_odds_by_events(
                    slug_key=slug_key,
                    fixtures=fixtures,
                )
                logger.debug("odds_loaded", count=len(odds_map), competition_id=str(competition_id), season=season)

                # Collect team + match + poisson features (via scopes)
                scopes_features = await service_team_features.extract_features_scopes(
                    events=fixtures,
                    team_ids_set=team_ids_set,
                    competition_id=competition_id,
                    season=season,
                )
                logger.debug("scopes_features_extracted", competition_id=str(competition_id), season=season)

                # Collect model outputs (Elo + Poisson models)
                model_scopes = await service_layer_models.extract_model_scopes(
                    events=fixtures,
                    competition_id=competition_id,
                    season=season,
                )
                logger.debug("model_scopes_extracted", competition_id=str(competition_id), season=season)

                # Build unified input DTO
                build_input = service_event_layer.el_builder.build_input(
                    fixtures=fixtures,
                    odds_map=odds_map,
                    scopes_features=scopes_features,
                    model_scopes=model_scopes,
                )
                logger.debug("build_input_created", competition_id=str(competition_id), season=season)

                # Build final bundles
                bundles = service_event_layer.el_builder.build_bundles(build_input)
                logger.debug("bundles_built", count=len(bundles), competition_id=str(competition_id), season=season)

                # Persist (DB + cache)
                saved_count = await service_event_layer.persist_enriched_events(
                    bundles=bundles,
                    competition_id=competition_id,
                    season=season,
                )
                logger.debug(
                    "bundles_persisted",
                    saved=saved_count,
                    competition_id=str(competition_id),
                    season=season,
                )

                # Return minimal result
                last_result = {
                    "status": "ok",
                    "fixtures": str(len(fixtures)),
                    "bundles_saved": str(saved_count),
                }
                events_processed_total.inc(len(fixtures))

            except Exception as exc:
                logger.error(
                    "event_feature_bundle_collect_failed",
                    slug_key=slug_key,
                    competition_id=str(competition_id) if competition_id else None,
                    error=str(exc),
                    exc_info=True,
                )
                collection_errors_total.inc()

        return last_result if last_result else {"status": "ok", "fixtures": "0", "bundles_saved": "0"}
    except Exception as e:
        logger.error("event_feature_bundle_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}

@broker.task()
async def collect_event_edges_task() -> Dict[str, str]:
    """Collect and persist event edges from enriched bundles."""
    logger.debug("collect_event_edges_task_started")

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    container = broker.state.container
    provider = "odds_api"

    try:
        # Resolve services via DI
        service_team_features = create_team_features_service(container)
        service_event_layer = create_event_layer_service(container)

        policy_loader = container.policy_loader
        catalog_helper = service_team_features.catalog_cache_helper

        api_football_policy = policy_loader.get_api_football(provider)
        if not api_football_policy or not api_football_policy.competitions:
            logger.warning("no_api_football_policy_found", provider=provider)
            return {"status": "ok", "saved": "0"}

        total_saved = 0
        for slug_key, comp_config in api_football_policy.competitions.items():
            competition_id = None
            try:
                season = comp_config.seasons.current

                competitions = await catalog_helper.get_competitions_by_slugs("soccer", [slug_key])
                if not competitions:
                    logger.warning("competition_not_found", slug_key=slug_key)
                    continue

                competition = competitions[0]
                competition_id = competition.id

                logger.debug(
                    "event_edges_competition_processing",
                    competition_id=str(competition_id),
                    season=season,
                    slug_key=slug_key,
                )

                # Load fixtures
                fixtures, team_ids = await service_team_features.get_events_by_competition(
                    competition_id,
                    season,
                )
                if not fixtures:
                    logger.debug("no_fixtures_found", competition_id=str(competition_id), season=season)
                    continue

                # Extract event_ids
                event_ids = service_team_features.extract_event_ids(fixtures)

                # Load bundles (cache + repo)
                bundles = await service_event_layer.load_enriched_bundles(event_ids)

                # Compute edges (explicit edge_source - TODO: may be externalized to policy/config)
                edges_dict = service_event_layer.el_builder.compute_edges(bundles, edge_source="poisson")

                # Persist edges (DB + Cache)
                saved = await service_event_layer.save_edge_bundles(
                    edges_dict,
                    competition_id,
                    season,
                )

                logger.debug(
                    "edges_saved",
                    count=saved,
                    competition_id=str(competition_id),
                    season=season,
                )

                total_saved += saved

            except Exception as exc:
                logger.error(
                    "event_edges_collect_failed",
                    slug_key=slug_key,
                    competition_id=str(competition_id) if competition_id else None,
                    error=str(exc),
                    exc_info=True,
                )
                collection_errors_total.inc()

        return {"status": "ok", "saved": str(total_saved)}
    except Exception as e:
        logger.error("event_edges_task_failed", error=str(e), exc_info=True)
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}
