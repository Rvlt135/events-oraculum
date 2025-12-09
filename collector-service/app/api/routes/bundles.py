"""
Admin routes for collector-service.

These routes are mounted under /_admin prefix and provide:
- Manual task triggering
- Data inspection
- System management

Security: Should be protected at network level (ingress/proxy) or via admin token.
"""

from typing import Dict, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query

from app.api.dependencies import get_odds_service, get_event_layer_service
from app.config.security import verify_admin_token
from app.domain.entities.event_layer.dto import EventFeatureBundleDTO
from app.services.event_layer.event_layer_service import EventLayerService

# from app.infrastructure.di.services import get_events_service

logger = structlog.get_logger()

router = APIRouter(tags=["bundles"])


@router.get("/events/bundles", response_model=list[EventFeatureBundleDTO])
async def get_event_bundles(
    # slug_key: str,
    service: EventLayerService = Depends(get_event_layer_service),
    event_ids: list[UUID] = Query("9bb6b4aa-f57c-43ae-bdc8-36e7d21b6008", description="List of event IDs"),
    _auth: None = Depends(verify_admin_token),
) -> list[EventFeatureBundleDTO]:
    """Get event feature bundles for specified event IDs.
    
    Args:
        # slug_key: Competition slug key (for logging).
        service: Event layer service instance.
        event_ids: List of event identifiers to fetch bundles for.
        _auth: Admin token verification.
        
    Returns:
        List of EventFeatureBundleDTO instances.
    """
    # logger.info("get_event_bundles_started", slug_key=slug_key, count=len(event_ids))
    
    try:
        # Validation
        if not event_ids:
            raise HTTPException(status_code=400, detail="event_ids required")
        
        # Service call
        bundles = await service.get_events_bundles(event_ids)
        
        # Prepare response (bundles is already list[EventFeatureBundleDTO])
        logger.info("get_event_bundles_completed", returned=len(bundles))
        return bundles
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_event_bundles_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to load event bundles")


@router.get("events/edges")
async def get_event_edges(
    slug_key: str,
    service: EventLayerService = Depends(get_event_layer_service),
    event_ids: list[UUID] = Query(..., description="List of event IDs"),
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
        bundles = await service.get_events_edges(event_ids)

        if not bundles:
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