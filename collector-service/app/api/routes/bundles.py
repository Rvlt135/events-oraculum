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
from app.domain.entities.event_layer.dto import EventFeatureBundleDTO, EventEdgeDTO
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


@router.get("/events/edges", response_model=list[EventEdgeDTO])
async def get_event_edges(
    event_ids: list[UUID] = Query(..., description="List of event IDs"),
    service: EventLayerService = Depends(get_event_layer_service),
    _auth: None = Depends(verify_admin_token),
) -> list[EventEdgeDTO]:
    """Get event edges for specified event IDs.
    
    Args:
        event_ids: List of event identifiers to fetch edges for.
        service: Event layer service instance.
        _auth: Admin token verification.
        
    Returns:
        List of EventEdgeDTO instances.
    """
    logger.info("get_event_edges_started", count=len(event_ids))
    
    try:
        # Call service method
        edges_map: dict[UUID, EventEdgeDTO] = await service.get_edges(event_ids)
        
        # Convert result dict → ordered list
        result: list[EventEdgeDTO] = [edges_map[eid] for eid in event_ids if eid in edges_map]
        
        logger.info("get_event_edges_completed", count=len(result))
        return result
        
    except Exception as e:
        logger.error("get_event_edges_failed", event_ids_count=len(event_ids), error=str(e))
        raise HTTPException(status_code=500, detail="failed_to_load_edges")