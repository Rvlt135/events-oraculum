"""
Admin routes for odds-service.

These routes are mounted under /_admin prefix and provide:
- Manual task triggering
- Data inspection
- System management

Security: Should be protected at network level (ingress/proxy) or via admin token.
"""

from typing import Optional, List, Literal
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from redis.asyncio import Redis

from app.api.schemas.schemas import (
    TaskTriggerResponse,
    SnapshotsResponse,
    SnapshotSummary,
    SportDTO,
    CompetitionDTO,
)
from app.api.dependencies import get_db_session, get_sports_service
from app.config.security import verify_admin_token
from app.tasks.collector import collect_sports_task, collect_odds_task
from app.infrastructure.repositories import NormalizedOddsRepository

logger = structlog.get_logger()

router = APIRouter(tags=["admin"])


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
    competition: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    _auth: None = Depends(verify_admin_token),
) -> SnapshotsResponse:
    """
    Get normalized odds snapshots.

    Returns aggregated odds data with averages and best odds
    from multiple bookmakers.
    """
    logger.info("fetching_snapshots", limit=limit, competition=competition)

    try:
        normalized_repo = NormalizedOddsRepository(session)
        snapshots_data = await normalized_repo.get_normalized_snapshots(
            limit=limit,
            competition_key=competition
        )

        snapshots = [SnapshotSummary.model_validate(snap, by_alias=True) for snap in snapshots_data]

        return SnapshotsResponse(
            count=len(snapshots),
            limit=limit,
            competition=competition,
            snapshots=snapshots,
        )

    except Exception as e:
        logger.error("failed_to_fetch_snapshots", error=str(e))
        raise


@router.post("/collect/sports", response_model=TaskTriggerResponse)
async def trigger_collection_sport(
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


@router.get("/catalog/sports", response_model=List[SportDTO])
async def get_sports_catalog(
    plan: Literal["free", "pro", "all_available"] = Query(
        default="all_available",
        description="Filter by plan type: free, pro, or all_available"
    ),
    sports_service = Depends(get_sports_service),
    _auth: None = Depends(verify_admin_token),
) -> List[SportDTO]:
    """
    Get sports catalog with cache-first strategy.

    Returns sports filtered by plan visibility:
    - free: Only sports with plan_visibility == "free"
    - pro: Only sports with plan_visibility == "pro"
    - all_available: All sports except unavailable

    Data source: Redis cache → DB fallback with cache warming
    """
    logger.info("get_sports_catalog_endpoint", plan=plan)

    try:
        sports = await sports_service.get_sports_catalog(plan)

        logger.info("sports_catalog_returned", plan=plan, count=len(sports))
        return sports

    except Exception as e:
        logger.error("failed_to_get_sports_catalog", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch sports catalog")


@router.get("/catalog/competitions", response_model=List[CompetitionDTO])
async def get_competitions_catalog(
    category: str = Query(..., description="Sport category (e.g., soccer, tennis)"),
    plan: Literal["free", "pro", "all_available"] = Query(
        default="all_available",
        description="Filter by plan type: free, pro, or all_available"
    ),
    sports_service = Depends(get_sports_service),
    _auth: None = Depends(verify_admin_token),
) -> List[CompetitionDTO]:
    """
    Get competitions catalog for a specific category with cache-first strategy.

    Returns competitions filtered by plan visibility:
    - free: Only competitions with plan_visibility == "free"
    - pro: Only competitions with plan_visibility == "pro"
    - all_available: All competitions except unavailable

    Args:
        category: Required sport category (e.g., 'soccer')
        plan: Plan filter type

    Data source: Redis cache → DB fallback with cache warming
    """
    logger.info("get_competitions_catalog_endpoint", category=category, plan=plan)

    if not category:
        raise HTTPException(status_code=400, detail="category parameter is required")

    try:
        competitions = await sports_service.get_competitions_catalog(category, plan)

        logger.info("competitions_catalog_returned", category=category, plan=plan, count=len(competitions))
        return competitions

    except Exception as e:
        logger.error("failed_to_get_competitions_catalog", category=category, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch competitions catalog")


@router.post("/tasks/events/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_events_sync(
    _auth: None = Depends(verify_admin_token)
) -> TaskTriggerResponse:
    """
    Manually trigger events collection task (E10).

    This enqueues a `collect_events` task in TaskIQ that will:
    1. Load provider_policy.yml configuration
    2. Determine active competitions (cache-first with DB fallback)
    3. Collect events for each competition with rate limits
    4. Refresh events cache atomically per competition
    5. Log summary with inserted/updated/skipped counts

    No runtime parameters - all configuration from provider_policy.yml.
    """
    logger.info("events_sync_triggered_manually")

    try:
        from app.tasks.collector import collect_events

        task = await collect_events.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="Events collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_events_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )


@router.get("/catalog/events/upcoming")
async def get_upcoming_events_catalog(
    _auth: None = Depends(verify_admin_token),
):
    """
    Get upcoming events from process cache (E10).

    Returns flat list of upcoming events aggregated from all enabled competitions.
    Data source: catalog:events:{provider_key}:upcoming cache keys.

    No filters, no pagination - returns up to limit from provider_policy.admin.events_view_limit.
    """
    logger.info("get_upcoming_events_catalog_endpoint")

    try:
        from app.infrastructure.di.services import get_events_service

        events_service = await get_events_service()
        events = await events_service.get_upcoming_events_from_cache()

        logger.info("upcoming_events_returned", count=len(events))
        return {
            "count": len(events),
            "events": events
        }

    except Exception as e:
        logger.error("failed_to_get_upcoming_events", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch upcoming events")
