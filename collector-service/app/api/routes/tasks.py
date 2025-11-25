from typing import Optional, List, Literal, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Query, Depends, HTTPException, Request
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
# from app.infrastructure.di.services import get_events_service

from app.api.dependencies import get_db_session, get_sports_service, get_events_service, get_odds_service, get_redis_cache
from app.config.security import verify_admin_token
from app.tasks.collector import collect_sports_task, collect_events, collect_standings_football_task, collect_odds_task, collect_fixtures_football_task
from app.tasks.prioritizer import prioritize_all
from app.tasks.sync_teams import sync_teams_from_api_football
from app.infrastructure.repositories import NormalizedOddsRepository

logger = structlog.get_logger()

router = APIRouter(tags=["admin_tasks"])

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

@router.post("/events/sync", response_model=TaskTriggerResponse, status_code=202)
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


@router.post("/priorities/run", response_model=TaskTriggerResponse)
async def trigger_prioritization(
        request: Request,
        _auth: None = Depends(verify_admin_token)
) -> TaskTriggerResponse:
    """
    Manually trigger event prioritization.

    Enqueues single prioritize_all task.

    Returns 202 with task_id.
    """
    logger.info("prioritization_triggered_manually")

    try:
        container = request.app.state.container
        policy_loader = container.policy_loader

        providers = policy_loader.get_providers()
        provider = providers[0] if providers else "odds_api"

        prioritizer_policy = policy_loader.get_prioritizer_policy(provider)
        if not prioritizer_policy:
            return TaskTriggerResponse(
                status="error",
                message=f"Policy not found for provider: {provider}",
            )

        if not prioritizer_policy.enabled:
            return TaskTriggerResponse(
                status="skipped",
                message="Prioritization disabled in policy",
            )

        task = await prioritize_all.kiq()
        logger.info("prioritize_all_enqueued", task_id=task.task_id)

        return TaskTriggerResponse(
            status="enqueued",
            message="Prioritize all task enqueued",
            task_id=str(task.task_id),
        )

    except Exception as e:
        logger.error("failed_to_enqueue_prioritization", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )


@router.post("/odds/collect", response_model=TaskTriggerResponse, status_code=202)
async def trigger_odds_collection(
        _auth: None = Depends(verify_admin_token)
) -> TaskTriggerResponse:
    """
    Manually trigger odds collection task (O1-T7).

    This enqueues a `collect_odds_task` in TaskIQ that will:
    1. Load provider_policy.yml configuration
    2. Determine competitions with upcoming events (cache-first with DB fallback)
    3. Fetch odds from external API for each competition
    4. Normalize odds to snapshots and aggregated normalized odds
    5. Upsert to database (idempotent)
    6. Update odds cache atomically per event
    7. Log summary with events_count, events_with_odds, snapshots_written, etc.

    No runtime parameters - all configuration from provider_policy.yml.
    """
    logger.info("odds_collection_triggered_manually")

    try:
        task = await collect_odds_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="Odds collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_odds_collection", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )

@router.post("/sync/teams", response_model=TaskTriggerResponse, status_code=202)
async def trigger_teams_sync_from_api_football(
        request: Request,
        provider: str = Query(default="odds_api", description="Provider name"),
        _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """
    Manually trigger teams sync from API Football.

    This enqueues a `sync_teams_from_api_football` task in TaskIQ that will:
    1. Load API Football configuration from provider_policy.yml
    2. Fetch teams for each configured competition
    3. Upsert teams to database using team_slug as unique identifier

    Args:
        request: FastAPI request object
        provider: Provider name (default: "odds_api")
        _auth: Authorization object
    """
    logger.info("teams_sync_from_api_football_triggered_manually", provider=provider)

    try:
        container = request.app.state.container
        policy_loader = container.policy_loader

        api_fb = policy_loader.get_api_football(provider)
        competitions_list = list(api_fb.competitions.keys()) if api_fb else []

        logger.info(
            "teams_sync_enqueuing",
            provider=provider,
            competitions_count=len(competitions_list),
            competitions=competitions_list
        )

        task = await sync_teams_from_api_football.kiq(provider=provider)

        return TaskTriggerResponse(
            status="queued",
            message=f"Teams sync task enqueued for {len(competitions_list)} competitions",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_teams_sync", provider=provider, error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )

@router.post("/standings/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_standings_sync(
    _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """
    Manually trigger standings sync from API Football.

    This enqueues a `collect_standings_football_task` task in TaskIQ.
    """
    logger.info("standings_sync_triggered_manually")

    try:
        task = await collect_standings_football_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="Standings collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_standings_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )

@router.post("/fixtures/sync", response_model=TaskTriggerResponse, status_code=202)
async def trigger_fixtures_sync(
    _auth: None = Depends(verify_admin_token),
) -> TaskTriggerResponse:
    """
    Manually trigger standings sync from API Football.

    This enqueues a `collect_standings_football_task` task in TaskIQ.
    """
    logger.info("standings_sync_triggered_manually")

    try:
        task = await collect_fixtures_football_task.kiq()

        return TaskTriggerResponse(
            status="enqueued",
            message="Standings collection task enqueued",
            task_id=str(task.task_id),
        )
    except Exception as e:
        logger.error("failed_to_enqueue_standings_sync", error=str(e))
        return TaskTriggerResponse(
            status="error",
            message=f"Failed to enqueue task: {str(e)}",
        )
