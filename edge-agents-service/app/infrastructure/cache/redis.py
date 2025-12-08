from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
import json
import redis.asyncio as redis
import structlog

from app.config.settings import settings
from app.infrastructure.cache.redis_client import RedisCacheClient

logger = structlog.get_logger()


class RecommendationCache:
    def __init__(self, client: RedisCacheClient):
        self.client = client
        self.ttl = 86400 * 3

    async def save_recommendation(
        self, event_id: UUID, recommendation: dict, ttl: Optional[int] = None
    ) -> None:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        key = f"rec:{event_id}"
        ttl_value = ttl if ttl is not None else self.ttl

        try:
            await self.client.rbd.set(key, json.dumps(recommendation), ex=ttl_value)
            logger.debug("recommendation_cached", event_id=str(event_id))
        except Exception as e:
            logger.error("cache_save_error", event_id=str(event_id), error=str(e))

    async def get_recommendation(self, event_id: UUID) -> Optional[dict]:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        key = f"rec:{event_id}"

        try:
            value = await self.client.rbd.get(key)
            if value:
                logger.debug("cache_hit", event_id=str(event_id))
                return json.loads(value)
            logger.debug("cache_miss", event_id=str(event_id))
            return None
        except Exception as e:
            logger.error("cache_get_error", event_id=str(event_id), error=str(e))
            return None

    async def add_to_list(
        self, league: str, date_key: str, recommendation: dict, max_size: int = 100
    ) -> None:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        list_key = f"rec:list:{league}:{date_key}"

        try:
            await self.client.rbd.lpush(list_key, json.dumps(recommendation))
            await self.client.rbd.ltrim(list_key, 0, max_size - 1)
            await self.client.rbd.expire(list_key, self.ttl)
            logger.debug("added_to_list", league=league, date=date_key)
        except Exception as e:
            logger.error("list_add_error", league=league, error=str(e))

    async def get_list(
        self, league: str, date_key: str, limit: int = 50
    ) -> List[dict]:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        list_key = f"rec:list:{league}:{date_key}"

        try:
            values = await self.client.rbd.lrange(list_key, 0, limit - 1)
            return [json.loads(v) for v in values]
        except Exception as e:
            logger.error("list_get_error", league=league, error=str(e))
            return []

    async def delete_recommendation(self, event_id: UUID) -> None:
        if not self.client:
            raise RuntimeError("Redis not initialized")

        key = f"rec:{event_id}"

        try:
            await self.client.rbd.delete(key)
            logger.debug("cache_deleted", event_id=str(event_id))
        except Exception as e:
            logger.error("cache_delete_error", event_id=str(event_id), error=str(e))


# recommendation_cache = RecommendationCache()
#
#
# async def get_recommendation_cache() -> RecommendationCache:
#     return recommendation_cache
