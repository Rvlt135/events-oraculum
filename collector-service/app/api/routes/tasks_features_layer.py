import structlog
from fastapi import APIRouter, Depends

from app.api.schemas.schemas import (
    TaskTriggerResponse,
)
from app.config.security import verify_admin_token
from app.tasks.feature_layer import collect_poisson_features_task, collect_team_features_task, \
    collect_match_features_task

# from app.infrastructure.di.services import get_events_service

logger = structlog.get_logger()

router = APIRouter(tags=["[L2] features_layer_tasks"])


@router.post("/features_team/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_feature_team_sync(
    _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """

    """
    logger.info("feature_team_sync_triggered_manually")

    try:
        task = await collect_team_features_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="feature_team collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_feature_team_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )

@router.post("/match_features/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_match_features_sync(
    _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """

    """
    logger.info("match_features_sync_triggered_manually")

    try:
        task = await collect_match_features_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="match_features collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_match_features_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )

@router.post("/poisson_features/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_poisson_features_sync(
    _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """

    """
    logger.info("poisson_features_sync_triggered_manually")

    try:
        task = await collect_poisson_features_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="poisson_features collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_poisson_features_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )