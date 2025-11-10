from __future__ import annotations
from typing import Any, Dict, Optional
import json
from redis.asyncio import Redis
from app.config.settings import settings

CATALOG_TTL_SEC = settings.catalog_cache_ttl
KEY_PREFIX = "catalog:sports"  # можно версионировать: v1:catalog:sports

def _key_catalog() -> str:
    return KEY_PREFIX  # если появится мультитенанси/планы — добавляй сегменты тут

class SportsCache:
    """Тонкий слой вокруг Redis с доменными методами для Sports."""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def set_catalog(self, items: Dict, ttl: int = CATALOG_TTL_SEC) -> None:
        """Store catalog in Redis as JSON string."""
        json_str = json.dumps(items, ensure_ascii=False)
        await self._r.setex(_key_catalog(), ttl, json_str)

    async def get_catalog(self) -> Optional[Dict[str, Any]]:
        """Retrieve catalog from Redis and parse JSON."""
        raw = await self._r.get(_key_catalog())
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
            logger.warning("cache_decode_error", error=str(e), raw_type=type(raw).__name__)
            await self.invalidate_catalog()
            return None

    async def invalidate_catalog(self) -> None:
        await self._r.delete(_key_catalog())
