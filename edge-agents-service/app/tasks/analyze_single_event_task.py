"""Task for analyzing a single event (debugging/testing version)."""
from typing import Dict, Any
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

collection_duration = Histogram("single_event_analyze_task_duration_seconds", "Time spent building event analysis")
events_processed_total = Counter("single_event_analyze_task_processed_total", "Total number of event analysis events processed")
collection_errors_total = Counter("single_event_analyze_task_errors_total", "Total number of collection errors")

@broker.task()
async def analyze_single_event_task(
    event_id: UUID,
    slug_key: str,
    category: str = "soccer",
) -> Dict[str, Any]:
    """
    Analyze a single event by event_id (lightweight version for debugging/testing).
    
    Loads competitions, filters events by event_id, builds input DTO,
    and enqueues individual event analysis task.
    
    Args:
        event_id: UUID of the event to analyze
        slug_key: Competition slug key
        category: Event category (default: "soccer")
        
    Returns:
        Dict with status and event_id
    """
    logger.debug("analyze_single_event_task_started", event_id=str(event_id), slug_key=slug_key)
    
    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")
    
    container: Container = broker.state.container
    
    try:
        # Resolve DI inside task
        event_bundle_service: EventBundleConsumer = create_event_bundle_consumer(container)
        
        # Load competitions for the given slug_key
        competitions = await event_bundle_service.get_catalog_competitions_by_slug_key(
            category=category,
            slugs=[slug_key],
        )
        
        logger.debug("competitions_loaded", count=len(competitions))
        
        # For each competition, load upcoming events and flatten into all_events
        all_events = []
        for competition in competitions:
            # Get season from competition API sources
            season = None
            if competition.api_sources and competition.api_sources.seasons:
                season = competition.api_sources.seasons.current
            
            if season is None:
                logger.debug("competition_missing_season", competition_id=str(competition.id))
                continue
            
            events = await event_bundle_service.get_upcoming_events(
                competition_id=competition.id,
                season=season
            )
            
            all_events.extend(events)
        
        logger.debug("total_events_loaded", count=len(all_events))
        
        # From all_events select ONLY the event where event.event_id == event_id
        target_event = None
        for event in all_events:
            if event.event_id == event_id:
                target_event = event
                break
        
        if target_event is None:
            logger.warning("event_not_found", event_id=str(event_id), slug_key=slug_key)
            return {"status": "not_found", "event_id": str(event_id)}
        
        logger.debug("event_filtered", event_id=str(event_id))
        
        # Extract filtered_event_ids
        filtered_event_ids = [event_id]
        
        # Load bundle/edge maps
        bundles_map = await event_bundle_service.get_events_bundles_map(filtered_event_ids)
        edge_map = await event_bundle_service.get_events_edge_map(filtered_event_ids)
        
        # Build input_dtos using merge_bundle_edge
        input_dtos = event_bundle_service.merge_bundle_edge(
            bundles_map=bundles_map,
            edge_map=edge_map,
            events=[target_event],
        )
        
        # Select input_event = input_dtos[0]
        input_event: AgentInputDTO = input_dtos[0]
        
        # Enqueue analyze_event_task(input_event)
        await analyze_event_task.kiq(input_event)
        
        logger.debug("task_enqueued", event_id=str(event_id))
        
        # Return format
        return {"status": "queued", "event_id": str(event_id)}
        
    except Exception as e:
        logger.error("analyze_single_event_task_failed", event_id=str(event_id), error=str(e))
        raise