"""
Admin routes for collector-service.

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
from app.tasks.sync_teams import sync_teams_from_api_football
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

@router.get("/catalog/events/upcoming")
async def get_upcoming_events_catalog(
    _auth: None = Depends(verify_admin_token),
    events_service = Depends(get_events_service),
):
    """
    Get upcoming events from process cache (E10).

    Returns flat list of upcoming events aggregated from all enabled competitions.
    Data source: catalog:events:{slug_key}:upcoming cache keys.

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


@router.get("/priority/{slug_key}")
async def get_priority_ranked(
    slug_key: str,
    redis: Redis = Depends(get_redis_cache),
    _auth: None = Depends(verify_admin_token),
):
    """
    Get ranked events for a competition from Redis.

    Reads priority:events:{slug_key}:ranked cache key.
    Returns ordered list of events with priorities or empty list if not found.
    """
    logger.info("get_priority_ranked_endpoint", slug_key=slug_key)

    cache_key = f"priority:events:{slug_key}:ranked"

    try:
        raw_events = await redis.lrange(cache_key, 0, -1)

        if not raw_events:
            logger.info("priority_ranked_not_found", slug_key=slug_key)
            return []

        import json
        events = []
        for raw_event in raw_events:
            try:
                event = json.loads(raw_event)
                events.append({
                    "event_id": event.get("id"),
                    "commence_time": event.get("commence_time"),
                    "priority": event.get("priority", 0.0),
                })
            except Exception as e:
                logger.warning("failed_to_parse_ranked_event", error=str(e))

        logger.info("priority_ranked_returned", slug_key=slug_key, count=len(events))
        return events

    except Exception as e:
        logger.error("failed_to_get_priority_ranked", slug_key=slug_key, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch ranked events")


@router.get("/odds/{event_id}")
async def get_event_odds(
    event_id: UUID,
    slug_key: Optional[str] = Query(default=None),
    odds_service = Depends(get_odds_service),
    _auth: None = Depends(verify_admin_token),
) -> Dict[str, Any]:
    """
    Get normalized odds for an event (cache-first, then DB).

    Reads from catalog:odds:{slug_key}:{event_id} cache or falls back to DB.
    Returns compact JSON with markets, averages, best odds, and bookmakers count.
    """
    logger.info("get_event_odds_endpoint", event_id=str(event_id), slug_key=slug_key)

    try:
        # If slug_key not provided, try to find it from events cache
        if not slug_key:
            # Try to find slug_key by searching events cache
            # This is a fallback - ideally slug_key should be provided
            logger.debug("slug_key_not_provided", event_id=str(event_id))

        odds_list = await odds_service.get_event_odds(
            slug_key=slug_key or "unknown",
            event_id=event_id
        )

        if not odds_list:
            return {
                "event_id": str(event_id),
                "slug_key": slug_key,
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
            "slug_key": slug_key,
            "has_odds": True,
            "markets": markets
        }

    except Exception as e:
        logger.error("failed_to_get_event_odds", event_id=str(event_id), error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch event odds")


@router.get("/catalog/odds/{slug_key}")
async def get_odds_catalog(
    slug_key: str,
    odds_service = Depends(get_odds_service),
    _auth: None = Depends(verify_admin_token),
) -> Dict[str, Any]:
    """
    Get upcoming events with odds availability for a competition.

    Reads normalized odds from Redis (catalog:odds:{slug_key}:{event_id}),
    supplements with basic event info from events cache if available.
    Does not fail if event info is missing.
    """
    logger.info("get_odds_catalog_endpoint", slug_key=slug_key)

    try:
        # Get upcoming events from events cache
        upcoming_events = await odds_service.events_cache.read_upcoming(slug_key)

        if not upcoming_events:
            return {
                "slug_key": slug_key,
                "count": 0,
                "items": []
            }

        items = []
        for event in upcoming_events:
            try:
                # Read normalized odds from odds cache
                odds_list = await odds_service.odds_cache.read_event_odds(
                    slug_key=slug_key,
                    event_id=event.id
                )
                has_odds = len(odds_list) > 0
            except Exception as e:
                logger.debug(
                    "failed_to_read_odds_for_event",
                    slug_key=slug_key,
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
            "slug_key": slug_key,
            "count": len(items),
            "items": items
        }

    except Exception as e:
        logger.error("failed_to_get_odds_catalog", slug_key=slug_key, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch odds catalog")