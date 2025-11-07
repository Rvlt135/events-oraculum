import redis.asyncio as redis
from typing import Optional
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class RedisManager:
    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def initialize(self) -> None:
        if not self.client:
            self.client = await redis.from_url(settings.redis_url, decode_responses=True)
            logger.info("redis_initialized")

    async def dispose(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("redis_disposed")

    async def get_client(self) -> redis.Redis:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return self.client

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        client = await self.get_client()
        await client.set(key, value, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        client = await self.get_client()
        return await client.get(key)

    async def delete(self, key: str) -> None:
        client = await self.get_client()
        await client.delete(key)

    async def setex(self, key: str, time: int, value: str) -> None:
        client = await self.get_client()
        await client.setex(key, time, value)


redis_manager = RedisManager()


async def get_redis() -> redis.Redis:
    return await redis_manager.get_client()
