"""
Redis client factory and cache utilities.
"""
from app.infrastructure.redis_client import RedisManager

# Global singleton for Redis manager
_redis_manager: RedisManager | None = None


def get_redis_manager() -> RedisManager:
    """Get Redis manager (create singleton if not exists)."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


async def initialize_redis() -> None:
    """Initialize Redis client."""
    manager = get_redis_manager()
    await manager.initialize()


async def dispose_redis() -> None:
    """Dispose Redis client."""
    manager = get_redis_manager()
    await manager.dispose()
