from __future__ import annotations
from typing import Any, Dict, Optional
import json
from redis.asyncio import Redis

CATALOG_TTL_SEC = 600  # 10 минут
KEY_PREFIX = "catalog:sports"  # можно версионировать: v1:catalog:sports

def _key_catalog() -> str:
    return KEY_PREFIX  # если появится мультитенанси/планы — добавляй сегменты тут

class SportsCache:
    """Тонкий слой вокруг Redis с доменными методами для Sports."""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def set_catalog(self, items: Dict, ttl: int = CATALOG_TTL_SEC) -> None:
        await self._r.setex(_key_catalog(), ttl, json.dumps(items))

    async def get_catalog(self) -> Optional[Dict[str, Any]]:
        raw = await self._r.get(_key_catalog())
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            await self.invalidate_catalog()
            return None

    async def invalidate_catalog(self) -> None:
        await self._r.delete(_key_catalog())
