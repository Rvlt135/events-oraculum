from typing import Optional
import json
import redis.asyncio as redis
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class RedisCache:
    def __init__(self):
        self.ttl = settings.cache_ttl_seconds
        self.client: Optional[redis.Redis] = None

    async def initialize(self) -> None:
        if not self.client:
            self.client = await redis.from_url(settings.redis_url, decode_responses=True)
            logger.info("redis_cache_initialized")

    async def dispose(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("redis_cache_disposed")

    async def get(self, key: str) -> Optional[dict]:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        try:
            value = await self.client.get(key)
            if value:
                logger.debug("cache_hit", key=key)
                return json.loads(value)
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

    async def delete(self, key: str) -> None:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        try:
            await self.client.delete(key)
            logger.debug("cache_delete", key=key)
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))


redis_cache_manager = RedisCache()


async def get_redis_cache() -> RedisCache:
    return redis_cache_manager
