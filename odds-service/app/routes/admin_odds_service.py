from fastapi import APIRouter, Depends
import structlog

from app.schemas.schemas import (
    TaskTriggerResponse,
)
from app.config.security import verify_admin_token
from app.tasks.collector import collect_odds_task, collect_sports_task

logger = structlog.get_logger()

router = APIRouter(tags=["admin"])


@router.post("/collect/sports", response_model=TaskTriggerResponse)
async def trigger_collection(
    _auth: None = Depends(verify_admin_token)
) -> TaskTriggerResponse:
    """
    Manually trigger odds collection task.

    This enqueues a collection task in TaskIQ that will:
    1. Fetch odds from external API
    2. Normalize team names
    3. Store events and odds snapshots
    4. Calculate aggregated odds
    """
    logger.info("manual_collection_triggered")

    try:
        task = await collect_sports_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="Collection task enqueued in TaskIQ",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_task", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )