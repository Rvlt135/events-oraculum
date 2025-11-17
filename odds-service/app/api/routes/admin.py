"""
Admin routes for odds-service.

These routes are mounted under /_admin prefix and provide:
- Manual task triggering
- Data inspection
- System management

Security: Should be protected at network level (ingress/proxy) or via admin token.
"""

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
from app.tasks.collector import collect_sports_task, collect_events, collect_odds_task
from app.tasks.prioritizer import prioritize_all
from app.infrastructure.repositories import NormalizedOddsRepository

logger = structlog.get_logger()

router = APIRouter(tags=["admin"])



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
    events_service = Depends(get_events_service),
):
    """
    Get upcoming events from process cache (E10).

    Returns flat list of upcoming events aggregated from all enabled competitions.
    Data source: catalog:events:{provider_key}:upcoming cache keys.

    No filters, no pagination - returns up to limit from provider_policy.admin.events_view_limit.
    """
    logger.info("get_upcoming_events_catalog_endpoint")

    try:
        events = await events_service.get_upcoming_events_from_cache()

        logger.info("upcoming_events_returned", count=len(events))
        return {
            "count": len(events),
            "events": events
        }

    except Exception as e:
        logger.error("failed_to_get_upcoming_events", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch upcoming events")


@router.post("/tasks/priorities/run", response_model=TaskTriggerResponse)
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


@router.get("/priority/{provider_key}")
async def get_priority_ranked(
    provider_key: str,
    redis: Redis = Depends(get_redis_cache),
    _auth: None = Depends(verify_admin_token),
):
    """
    Get ranked events for a competition from Redis.

    Reads priority:events:{provider_key}:ranked cache key.
    Returns ordered list of events with priorities or empty list if not found.
    """
    logger.info("get_priority_ranked_endpoint", provider_key=provider_key)

    cache_key = f"priority:events:{provider_key}:ranked"

    try:
        raw_events = await redis.lrange(cache_key, 0, -1)

        if not raw_events:
            logger.info("priority_ranked_not_found", provider_key=provider_key)
            return []

        import json
        events = []
        for raw_event in raw_events:
            try:
                event = json.loads(raw_event)
                events.append({
                    "event_id": event.get("id"),
                    "commence_time": event.get("commence_time"),
                    "priority": event.get("score", 0.0),
                })
            except Exception as e:
                logger.warning("failed_to_parse_ranked_event", error=str(e))

        logger.info("priority_ranked_returned", provider_key=provider_key, count=len(events))
        return events

    except Exception as e:
        logger.error("failed_to_get_priority_ranked", provider_key=provider_key, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch ranked events")


@router.get("/odds/{event_id}")
async def get_event_odds(
    event_id: UUID,
    provider_key: Optional[str] = Query(default=None),
    odds_service = Depends(get_odds_service),
    _auth: None = Depends(verify_admin_token),
) -> Dict[str, Any]:
    """
    Get normalized odds for an event (cache-first, then DB).

    Reads from catalog:odds:{provider_key}:{event_id} cache or falls back to DB.
    Returns compact JSON with markets, averages, best odds, and bookmakers count.
    """
    logger.info("get_event_odds_endpoint", event_id=str(event_id), provider_key=provider_key)

    try:
        # If provider_key not provided, try to find it from events cache
        if not provider_key:
            # Try to find provider_key by searching events cache
            # This is a fallback - ideally provider_key should be provided
            logger.debug("provider_key_not_provided", event_id=str(event_id))

        odds_list = await odds_service.get_event_odds(
            provider_key=provider_key or "unknown",
            event_id=event_id
        )

        if not odds_list:
            return {
                "event_id": str(event_id),
                "provider_key": provider_key,
                "has_odds": False,
                "markets": []
            }

        markets = []
        for odds in odds_list:
            markets.append({
                "market_type": odds.market_type,
                "home_odds_avg": float(odds.home_odds_avg),
                "away_odds_avg": float(odds.away_odds_avg),
                "draw_odds_avg": float(odds.draw_odds_avg) if odds.draw_odds_avg else None,
                "home_odds_best": float(odds.home_odds_best),
                "away_odds_best": float(odds.away_odds_best),
                "draw_odds_best": float(odds.draw_odds_best) if odds.draw_odds_best else None,
                "bookmakers_count": odds.bookmakers_count,
                "timestamp_source": odds.timestamp_source.isoformat(),
                "timestamp_normalized": odds.timestamp_normalized.isoformat(),
            })

        return {
            "event_id": str(event_id),
            "provider_key": provider_key,
            "has_odds": True,
            "markets": markets
        }

    except Exception as e:
        logger.error("failed_to_get_event_odds", event_id=str(event_id), error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch event odds")


@router.get("/catalog/odds/{provider_key}")
async def get_odds_catalog(
    provider_key: str,
    odds_service = Depends(get_odds_service),
    _auth: None = Depends(verify_admin_token),
) -> Dict[str, Any]:
    """
    Get upcoming events with odds availability for a competition.

    Reads normalized odds from Redis (catalog:odds:{provider_key}:{event_id}),
    supplements with basic event info from events cache if available.
    Does not fail if event info is missing.
    """
    logger.info("get_odds_catalog_endpoint", provider_key=provider_key)

    try:
        # Get upcoming events from events cache
        upcoming_events = await odds_service.events_cache.read_upcoming(provider_key)

        if not upcoming_events:
            return {
                "provider_key": provider_key,
                "count": 0,
                "items": []
            }

        items = []
        for event in upcoming_events:
            try:
                # Read normalized odds from odds cache
                odds_list = await odds_service.odds_cache.read_event_odds(
                    provider_key=provider_key,
                    event_id=event.id
                )
                has_odds = len(odds_list) > 0
            except Exception as e:
                logger.debug(
                    "failed_to_read_odds_for_event",
                    provider_key=provider_key,
                    event_id=str(event.id),
                    error=str(e)
                )
                has_odds = False

            items.append({
                "event_id": str(event.id),
                "commence_time": event.commence_time.isoformat() if event.commence_time else None,
                "home_team": event.home_team_name or "",
                "away_team": event.away_team_name or "",
                "has_odds": has_odds
            })

        return {
            "provider_key": provider_key,
            "count": len(items),
            "items": items
        }

    except Exception as e:
        logger.error("failed_to_get_odds_catalog", provider_key=provider_key, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch odds catalog")

@router.post("/tasks/odds/collect", response_model=TaskTriggerResponse, status_code=202)
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