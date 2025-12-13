from datetime import datetime, date
from typing import Optional, List, Any
from uuid import UUID
import json
import redis.asyncio as redis
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

class RedisCacheClient:
    def __init__(self, raw_redis: redis.Redis):
        self.rbd = raw_redis
        self.r = raw_redis

    async def set_json(
        self,
        key: str,
        value: dict | list | Any,
        ttl: int | None = None,
    ) -> None:
        """
        Save JSON-serializable value to Redis cache.
        
        Args:
            key: Redis key
            value: JSON-serializable value (dict, list, or any JSON-compatible type)
            ttl: Optional time-to-live in seconds
        """
        try:
            # Convert value → JSON-safe string one time
            payload = json.dumps(value, ensure_ascii=False)
            
            # Save JSON to Redis
            await self.r.set(key, payload, ex=ttl)
            
            logger.debug(
                "set_json",
                key=key,
                ttl=ttl,
            )
        except Exception as e:
            logger.error("set_json_failed", key=key, error=str(e))
            raise

    async def get_json(self, key: str) -> Optional[dict]:
        raw = await self.rbd.get(key)
        return json.loads(raw)