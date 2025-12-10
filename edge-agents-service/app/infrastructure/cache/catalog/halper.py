import json
from typing import Any, Dict, Optional

import structlog
from redis.asyncio import Redis

from app.config.settings import settings
from app.infrastructure.cache import RedisCacheClient

CATALOG_TTL_SEC = settings.cache_ttl_competitions_sec
KEY_PREFIX_CATALOG_COMPETITIONS = "catalog:competitions"

logger = structlog.get_logger()

def _key_catalog_competitions(category: str) -> str:
    """Generate Redis key for competitions catalog teams by slug_key."""
    return f"{KEY_PREFIX_CATALOG_COMPETITIONS}:{category}"

class CatalogHalperCache:
    """Redis cache layer for competitions catalog."""

    def __init__(self, rdb_client: RedisCacheClient) -> None:
        self._r = rdb_client

    async def get_catalog_competitions(self, category: str) -> Optional[Dict[str, Any]]:
        """Retrieve competitions catalog for a specific category."""
        result = await self._r.get_json(_key_catalog_competitions(category))
        if not result:
            return None
        try:
            # Handle both string and bytes responses
            return result
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            # Log error and invalidate corrupted cache
            logger.warning("cache_decode_error", error=str(e), raw_type=type(result).__name__, category=category)
            return None