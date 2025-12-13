import json
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from redis.asyncio import Redis

from app.config.settings import settings
from app.domain.entities.agents.dto import MainAnalysisOutputDTO
from app.infrastructure.cache import RedisCacheClient

KEY_PREFIX_AGENT_EVENTS = "agent:events"

logger = structlog.get_logger()

def _key_agent_events(event_id: str) -> str:
    """Generate Redis key for agent events by event_id."""
    return f"{KEY_PREFIX_AGENT_EVENTS}:{event_id}"

class EventAnalysisCache:
    """Redis cache layer for event analysis outputs."""

    def __init__(self, rdb_client: RedisCacheClient) -> None:
        self._r = rdb_client

    async def save_event_analysis(
        self,
        event_id: UUID,
        main_output: MainAnalysisOutputDTO
    ) -> None:
        """
        Save event analysis outputs to Redis cache.
        
        Args:
            event_id: UUID of the event
            main_output: MainAnalysisOutputDTO containing aggregated analysis results
        """
        # Compute cache key
        key = _key_agent_events(str(event_id))
        
        # Prepare payload from main_output
        payload = main_output.model_dump(mode="json")
        
        # Get TTL from settings
        ttl = settings.AGENT_OUTPUT_TTL_SECONDS
        
        # Save to Redis using set_json
        await self._r.set_json(key, payload, ttl=ttl)
        
        logger.debug(
            "save_event_analysis",
            event_id=str(event_id),
            ttl=ttl,
            outputs_count=len(main_output.agents_outputs),
        )
