"""
Redis client manager with singleton pattern.
"""
import redis.asyncio as redis
from typing import Optional
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

_REDIS_CLIENT: Optional[redis.Redis] = None

def get_redis() -> redis.Redis:
    """Get client Redis if not initialize rise Error"""
    if _REDIS_CLIENT is None:
        raise RuntimeError("Redis not initialized. Call initialize() first.")
    return _REDIS_CLIENT

async def initialize_redis() -> None:
    """Initialize Redis client (for lifecycle management)."""
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = redis.from_url(settings.redis_url, decode_responses=True)
        logger.info("redis_initialized")

async def dispose_redis() -> None:
    """Dispose Redis client (for lifecycle management)."""
    global _REDIS_CLIENT
    if _REDIS_CLIENT:
        await _REDIS_CLIENT.close()
        _REDIS_CLIENT = None
        logger.info("redis_disposed")
