"""Task for analyzing individual events."""
import os

import structlog
from prometheus_client import Histogram, Counter

from app.domain.entities.agents.dto import AgentInputDTO
from app.infrastructure.di.container import Container
from app.infrastructure.di.service_factory import create_agents_pipeline, create_event_analysis_service
from app.pipelines.agents_pipeline import AgentsPipeline
from app.services.event_analysis import EventAnalysisService
from app.infrastructure.cache.redis_broker import RedisBrokerClient
from app.tasks.broker import broker

logger = structlog.get_logger()

collection_duration = Histogram("event_analysis_duration_seconds", "Time spent analyzing event")
events_processed_total = Counter("event_analysis_events_processed_total", "Total number of event analysis events processed")
collection_errors_total = Counter("event_analysis_collection_errors_total", "Total number of collection errors")

@broker.task()
async def analyze_event_task(input_event: AgentInputDTO) -> None:
    """
    Analyze a single event using agent pipeline.
    
    Args:
        input_event: AgentInputDTO containing event data, bundle, and edge information
    """
    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    container: Container = broker.state.container
    
    # Get DI dependencies from container
    agents_pipeline = create_agents_pipeline(container)
    event_analysis_service = create_event_analysis_service(container)
    redis_broker = container.redis_broker_client
    
    # (1) Compute keys
    event_id = input_event.event_id
    
    try:
        # (2) Try acquire Redis lock
        acquired = await redis_broker.acquire_lock(event_id)
        if not acquired:
            await redis_broker.set_status(event_id, "skipped_locked")
            logger.debug("analyze_event_task_skipped_locked", event_id=str(event_id))
            return

        logger.warning(
            "EXECUTING REAL TASK",
            event_id=str(input_event.event_id),
            worker=os.getpid(),
        )

        # (3) Set running status
        await redis_broker.set_status(event_id, "running")
        logger.debug("analyze_event_task_started", event_id=str(event_id))
        
        # (4) Run agent pipeline
        agent_outputs = await agents_pipeline.run_for_input(input_event)
        
        # (5) Run final aggregation
        main_output = await agents_pipeline.run_final(
            agent_outputs=agent_outputs,
            input_dto=input_event,
        )
        
        # (6) Save analysis results
        await event_analysis_service.save_agent_analysis_outputs(
            event_id=event_id,
            main_output=main_output
        )
        
        # (7) Set success status
        await redis_broker.set_status(event_id, "success")
        
        # (8) Release lock
        await redis_broker.release_lock(event_id)
        
        logger.debug(
            "analyze_event_task_completed",
            event_id=str(event_id),
            agents_count=len(agent_outputs),
            main_score=main_output.aggregated_score,
        )
        
    except Exception as e:
        # Error flow: Set failed status and release lock
        await redis_broker.set_status(event_id, "failed")
        await redis_broker.release_lock(event_id)
        
        logger.error(
            "analyze_event_task_failed",
            event_id=str(event_id),
            error=str(e),
        )
        
        # Re-raise exception for TaskIQ error pipeline
        raise
