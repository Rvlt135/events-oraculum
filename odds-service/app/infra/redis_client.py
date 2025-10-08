import redis.asyncio as redis
from typing import Optional
import structlog

logger = structlog.get_logger()


class RedisClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        if not self.client:
            self.client = await redis.from_url(self.url, decode_responses=True)
            logger.info("redis_connected", url=self.url)

    async def disconnect(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("redis_disconnected")

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        if not self.client:
            await self.connect()
        await self.client.set(key, value, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        if not self.client:
            await self.connect()
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        if not self.client:
            await self.connect()
        await self.client.delete(key)
