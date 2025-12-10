from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
import json
import redis.asyncio as redis
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

class RedisCacheClient:
    def __init__(self, raw_redis: redis.Redis):
        self.rbd = raw_redis

    async def set_json(self, key: str, value: dict, ttl: int | None = None):
        payload = json.dumps(value)
        await self.rbd.set(key, payload, ex=ttl)

    async def get_json(self, key: str) -> Optional[dict]:
        raw = await self.rbd.get(key)
        return json.loads(raw)