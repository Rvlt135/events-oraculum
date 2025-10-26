"""
DI for Redis client and caches.
"""
from app.infra.rdb.client import get_redis_manager


def get_redis_client():
    """Get Redis client for DI."""
    return get_redis_manager()
