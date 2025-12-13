"""Task for starting event analysis workflow."""
from typing import Dict, List, Any
from uuid import UUID

import structlog
from prometheus_client import Histogram, Counter

from app.domain.entities.agents.dto import AgentInputDTO
from app.domain.entities.collector_api.dto import CompetitionReadDTO, UpcomingEventCatalogDTO
from app.infrastructure.di.container import Container
from app.infrastructure.di.service_factory import create_event_bundle_consumer
from app.services.event_bundle_consumer import EventBundleConsumer
from app.tasks.broker import broker
from app.tasks.analyze_event_task import analyze_event_task

logger = structlog.get_logger()

collection_duration = Histogram("start_event_analysis_collection_duration_seconds", "Time spent building event analysis")
events_processed_total = Counter("start_event_analysis_events_processed_total", "Total number of event analysis events processed")
collection_errors_total = Counter("start_event_analysis_collection_errors_total", "Total number of collection errors")

@broker.task()
async def start_event_analysis_task() -> Dict[str, Any]:
    """
    Start event analysis workflow.
    
    Loads competitions, collects event data, builds input DTOs,
    and enqueues individual event analysis tasks.
    
    Returns:
        Dict with status, competitions count, events count, and task_ids
    """
    logger.debug("start_event_analysis_task_started")
    
    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")
    
    container: Container = broker.state.container
    
    try:
        # Resolve services via DI
        event_bundle_service: EventBundleConsumer = create_event_bundle_consumer(container)
        
        # 1) Load competitions
        category = "soccer"
        slugs = ["soccer_uefa_champs_league"]
        
        competitions: List[CompetitionReadDTO] = await event_bundle_service.get_catalog_competitions_by_slug_key(
            category=category,
            slugs=slugs
        )
        
        logger.debug("competitions_loaded", count=len(competitions))
        
        # 2) For each competition, get upcoming events and collect event_ids
        all_events: List[UpcomingEventCatalogDTO] = []
        event_ids: List[UUID] = []
        
        for competition in competitions:
            # Get season from competition API sources
            season = None
            if competition.api_sources and competition.api_sources.seasons:
                season = competition.api_sources.seasons.current
            
            if season is None:
                logger.debug("competition_missing_season", competition_id=str(competition.id))
                continue
            
            events: List[UpcomingEventCatalogDTO] = await event_bundle_service.get_upcoming_events(
                competition_id=competition.id,
                season=season
            )
            
            all_events.extend(events)
            event_ids.extend([event.event_id for event in events])
        
        logger.debug("event_ids_loaded", count=len(event_ids))
        
        # 3) Load bundles and edges
        bundles_map = await event_bundle_service.get_events_bundles_map(event_ids)
        edge_map = await event_bundle_service.get_events_edge_map(event_ids)
        
        logger.debug("inputs_built", bundles_count=len(bundles_map), edge_count=len(edge_map))
        
        # 4) Build AgentInputDTO list via existing merge function
        input_dtos: List[AgentInputDTO] = event_bundle_service.merge_bundle_edge(
            bundles_map=bundles_map,
            edge_map=edge_map,
            events=all_events
        )
        
        logger.debug("input_dtos_built", count=len(input_dtos))
        
        # 5) For each dto in input_dtos, enqueue analyze_event_task
        task_ids: List[str] = []
        
        for input_dto in input_dtos:
            try:
                task = await analyze_event_task.kiq(input_dto)
                task_ids.append(str(task.task_id))
            except Exception as e:
                logger.warning("enqueue_task_failed", event_id=str(input_dto.event_id), error=str(e))
                continue
        
        logger.debug("tasks_enqueued", count=len(task_ids))
        
        # 6) Return JSON response
        return {
            "status": "scheduled",
            "competitions": len(competitions),
            "events": len(input_dtos),
            "task_ids": task_ids,
        }
        
    except Exception as e:
        logger.error("start_event_analysis_task_failed", error=str(e))
        raise
