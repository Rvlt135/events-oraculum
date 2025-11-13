from typing import Optional
import json
import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class RedisCache:
    def __init__(self, client: redis.Redis, ttl: int):
        self.ttl =  ttl # settings.cache_ttl_seconds
        self.client = client

    async def get(self, key: str) -> Optional[dict]:
        try:
            val = await self.client.get(key)
            if val:
                logger.debug("cache_hit", key=key)
                return json.loads(val)
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        try:
            ttl_value = ttl if ttl is not None else self.ttl
            await self.client.set(key, json.dumps(value), ex=ttl_value)
            logger.debug("cache_set", key=key, ttl=ttl_value)
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))

    async def set_json(self, key: str, payload: dict, ex: Optional[int] = None) -> None:
        try:
            await self.client.set(key, json.dumps(payload), ex=ex or self.ttl)
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))

    async def delete(self, key: str) -> None:
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))

