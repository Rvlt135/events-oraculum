from datetime import datetime, UTC
from typing import Any, Dict, Optional
import json
from uuid import UUID

from redis.asyncio import Redis

from app.infrastructure.db.orm import User

CATALOG_TTL_SEC = 300
KEY_SESSION_JTI = "session:{jti}"

def _key_session() -> str:
    return KEY_SESSION_JTI  # если появится мультитенанси/планы — добавляй сегменты тут


class SessionCache:
    """Session cache repository"""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def cache_session(self, jti: UUID, user_id: UUID, expires_at: datetime) -> None:
        key = _key_session().format(jti=jti)
        data = {
            "user_id": str(user_id),
            "expires_at": expires_at.isoformat(),
        }
        ttl = int((expires_at - datetime.now(UTC)).total_seconds())
        if ttl > 0:
            await self._r.set(key, json.dumps(data), ex=ttl)

    async def get_cached_session(self, jti: UUID) -> dict | None:
        key = _key_session().format(jti=jti)
        data = await self._r.get(key)
        if not data:
            return None
        return data

    async def invalidate_session(self, jti: UUID) -> None:
        key = _key_session().format(jti=jti)
        await self._r.delete(key)
