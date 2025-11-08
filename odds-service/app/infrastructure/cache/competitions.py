from __future__ import annotations
from typing import Any, Dict, Optional
import json
from redis.asyncio import Redis

CATALOG_TTL_SEC = 600  # 10 minutes
KEY_PREFIX = "catalog:competitions"


def _key_catalog(category: str) -> str:
    """Generate Redis key for competitions catalog by category."""
    return f"{KEY_PREFIX}:{category}"


class CompetitionsCache:
    """Redis cache layer for competitions catalog."""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def set_catalog(self, category: str, items: Dict, ttl: int = CATALOG_TTL_SEC) -> None:
        """Store competitions catalog for a specific category."""
        await self._r.setex(_key_catalog(category), ttl, json.dumps(items))

    async def get_catalog(self, category: str) -> Optional[Dict[str, Any]]:
        """Retrieve competitions catalog for a specific category."""
        raw = await self._r.get(_key_catalog(category))
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
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
