import structlog
from fastapi import APIRouter, Depends

from app.api.schemas.schemas import (
    TaskTriggerResponse,
)
from app.config.security import verify_admin_token
from app.tasks.models_layer import collect_layer_models_elo_task, collect_layer_models_poisson_task

# from app.infrastructure.di.services import get_events_service

logger = structlog.get_logger()

router = APIRouter(tags=["[L3] models_layer_tasks"])

@router.post("/layer_models/elo/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_layer_models_elo_sync(
    _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """

    """
    logger.info("layer_models_elo_sync_triggered_manually")

    try:
        task = await collect_layer_models_elo_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="layer_models_elo collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_layer_models_elo_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue layer_models_elo collection task: {str(e)}",
        )

@router.post("/layer_models/poisson/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_layer_models_elo_sync(
    _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """

    """
    logger.info("layer_models_elo_sync_triggered_manually")

    try:
        task = await collect_layer_models_poisson_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="layer_models_elo collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_layer_models_elo_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue layer_models_elo collection task: {str(e)}",
        )