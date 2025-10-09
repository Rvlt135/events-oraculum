"""
Admin routes for odds-service.

These routes are mounted under /_admin prefix and provide:
- Manual task triggering
- Data inspection
- System management

Security: Should be protected at network level (ingress/proxy) or via admin token.
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config.settings import settings
from app.domain.schemas import (
    TaskTriggerResponse,
    SnapshotsResponse,
    SnapshotSummary,
)
from app.infra.providers import get_db_session
from app.tasks.collector import collect_odds_task

logger = structlog.get_logger()

router = APIRouter(tags=["admin"])


async def verify_admin_token(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
) -> None:
    """
    Simple token-based admin authentication.

    If ADMIN_TOKEN is configured, validates the token from header.
    For production, use network-level security (IP allowlist, mTLS, auth proxy).
    """
    if settings.admin_token:
        if not x_admin_token or x_admin_token != settings.admin_token:
            logger.warning("admin_unauthorized_attempt", provided_token_exists=bool(x_admin_token))
            raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/tasks/collect", response_model=TaskTriggerResponse)
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
        task = await collect_odds_task.kiq()

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


@router.get("/data/snapshots", response_model=SnapshotsResponse)
async def get_snapshots(
    limit: int = Query(default=100, ge=1, le=1000),
    league: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    _auth: None = Depends(verify_admin_token),
) -> SnapshotsResponse:
    """
    Get normalized odds snapshots.

    Returns aggregated odds data with averages and best odds
    from multiple bookmakers.
    """
    logger.info("fetching_snapshots", limit=limit, league=league)

    try:
        from app.infra.repositories import NormalizedOddsRepository

        normalized_repo = NormalizedOddsRepository(session)
        snapshots_data = await normalized_repo.get_normalized_snapshots(
            limit=limit,
            league_key=league
        )

        snapshots = [SnapshotSummary.model_validate(snap) for snap in snapshots_data]

        return SnapshotsResponse(
            count=len(snapshots),
            limit=limit,
            league=league,
            snapshots=snapshots,
        )

    except Exception as e:
        logger.error("failed_to_fetch_snapshots", error=str(e))
        raise
