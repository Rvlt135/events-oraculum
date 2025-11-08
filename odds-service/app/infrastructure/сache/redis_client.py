"""
Redis client manager with singleton pattern.
"""
import redis.asyncio as redis
from typing import Optional
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class RedisManager:
    """
    Redis client manager with singleton pattern and lazy initialization.
    
    Singleton is implemented via __new__ method - only one instance exists.
    Multiple calls to RedisManager() return the same instance.
    """
    _instance: Optional["RedisManager"] = None
    
    def __new__(cls) -> "RedisManager":
        """Create singleton instance (only once)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis client (lazy - only when initialize() is called)."""
        # Initialize client only once (__init__ is called every time, but instance is the same)
        if not hasattr(self, '_client'):
            self._client: Optional[redis.Redis] = None

    async def initialize(self) -> None:
        """Initialize Redis client connection."""
        if not self._client:
            # from_url is a synchronous factory function that returns an async client
            self._client = redis.from_url(settings.redis_url, decode_responses=True)
            logger.info("redis_initialized")

    async def dispose(self) -> None:
        """Close Redis client connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("redis_disposed")

    @property
    def client(self) -> redis.Redis:
        """
        Get Redis client with automatic initialization check.
        
        Raises RuntimeError if Redis is not initialized.
        """
        if not self._client:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._client

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        """Set key-value pair in Redis."""
        await self.client.set(key, value, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        """Get value by key from Redis."""
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        """Delete key from Redis."""
        await self.client.delete(key)

    async def setex(self, key: str, time: int, value: str) -> None:
        """Set key-value pair with expiration time."""
        await self.client.setex(key, time, value)


def get_redis_manager() -> RedisManager:
    """
    Get Redis manager singleton instance.
    
    Returns the same instance every time (singleton pattern via __new__).
    """
    return RedisManager()


async def initialize_redis() -> None:
    """Initialize Redis client (for lifecycle management)."""
    await get_redis_manager().initialize()


async def dispose_redis() -> None:
    """Dispose Redis client (for lifecycle management)."""
    await get_redis_manager().dispose()


def get_redis_client() -> RedisManager:
    """Get Redis manager for dependency injection."""
    return get_redis_manager()
