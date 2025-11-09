from __future__ import annotations
from typing import Any, Dict, Optional
import json
from redis.asyncio import Redis

CATALOG_TTL_SEC = 600  # 10 minutes
KEY_PREFIX = "catalog:competitions"


def _normalize_category(category: str) -> str:
    """Normalize category name by replacing spaces with underscores."""
    return category.replace(" ", "_")


def _key_catalog(category: str) -> str:
    """Generate Redis key for competitions catalog by category."""
    normalized = _normalize_category(category)
    return f"{KEY_PREFIX}:{normalized}"


class CompetitionsCache:
    """Redis cache layer for competitions catalog."""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def set_catalog(self, category: str, items: Dict, ttl: int = CATALOG_TTL_SEC) -> None:
        """Store competitions catalog for a specific category."""
        json_str = json.dumps(items, ensure_ascii=False)
        await self._r.setex(_key_catalog(category), ttl, json_str)

    async def get_catalog(self, category: str) -> Optional[Dict[str, Any]]:
        """Retrieve competitions catalog for a specific category."""
        raw = await self._r.get(_key_catalog(category))
        if not raw:
            return None
        try:
            # Handle both string and bytes responses
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            # Log error and invalidate corrupted cache
            import structlog
            logger = structlog.get_logger()
            logger.warning("cache_decode_error", error=str(e), raw_type=type(raw).__name__, category=category)
            await self.invalidate_catalog(category)
            return None

    async def invalidate_catalog(self, category: str) -> None:
        """Invalidate competitions catalog for a specific category."""
        await self._r.delete(_key_catalog(category))

    async def invalidate_all(self) -> None:
        """Invalidate all competitions catalogs."""
        pattern = f"{KEY_PREFIX}:*"
        cursor = 0
        while True:
            cursor, keys = await self._r.scan(cursor, match=pattern, count=100)
            if keys:
                await self._r.delete(*keys)
            if cursor == 0:
                break
