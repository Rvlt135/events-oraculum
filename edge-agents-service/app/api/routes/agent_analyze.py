from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends

from app.config.security import verify_admin_token
from app.tasks.start_event_analysis_task import start_event_analysis_task
from app.tasks.analyze_single_event_task import analyze_single_event_task

router = APIRouter(prefix="/_agents", tags=["Agents Analyze"])

logger = structlog.get_logger()


@router.post("/analyze")
async def analyze(
        _auth: None = Depends(verify_admin_token)
) -> dict[str, Any]:
    """
    Manually trigger start_event_analysis_task.
    
    Returns:
        Dict with status, task_name, and task_id
    """
    logger.info("analyze_route_called")
    
    task = await start_event_analysis_task.kiq()
    
    return {
        "status": "scheduled",
        "task_name": "start_event_analysis_task",
        "task_id": str(task.task_id),
    }


@router.post("/analyze/event")
async def analyze_single_event(
    event_id: UUID,
    slug_key: str,
    category: str = "soccer",
    _auth: None = Depends(verify_admin_token),
) -> dict[str, Any]:
    """
    Enqueue analysis for a single event.
    
    Args:
        event_id: UUID of the event to analyze
        slug_key: Competition slug key
        category: Event category (default: "soccer")
        
    Returns:
        Dict with status, task_id, and event_id
    """
    logger.debug("single_event_analysis_enqueued", event_id=str(event_id), slug_key=slug_key)
    
    task = await analyze_single_event_task.kiq(event_id, slug_key, category)
    
    return {
        "status": "queued",
        "task_id": task.task_id,
        "event_id": str(event_id),
    }

