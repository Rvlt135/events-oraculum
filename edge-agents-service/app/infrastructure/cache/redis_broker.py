"""Redis broker client for task-related operations."""
import json
from typing import Optional
from uuid import UUID

import structlog
import redis.asyncio as aioredis

logger = structlog.get_logger()


class RedisBrokerClient:
    """Thin abstraction over aioredis client for task locks and status keys."""

    def __init__(self, redis: aioredis.Redis) -> None:
        """
        Initialize Redis broker client.
        
        Args:
            redis: aioredis Redis client instance
        """
        self.r = redis

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """
        Set a key-value pair in Redis.
        
        Args:
            key: Redis key
            value: String value to store
            ex: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.r.set(key, value, ex=ex)
            logger.debug("redis_set", key=key, ex=ex)
            return bool(result)
        except Exception as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            raise

    async def set_nx(self, key: str, value: str, ex: int) -> bool:
        """
        Set a key-value pair only if key does not exist (NX = Not eXists).
        
        Args:
            key: Redis key
            value: String value to store
            ex: Expiration time in seconds
            
        Returns:
            True if key was set, False if key already exists
        """
        try:
            result = await self.r.set(key, value, ex=ex, nx=True)
            logger.debug("redis_set_nx", key=key, ex=ex, success=bool(result))
            return bool(result)
        except Exception as e:
            logger.error("redis_set_nx_failed", key=key, error=str(e))
            raise

    async def get(self, key: str) -> str | None:
        """
        Get a value from Redis by key.
        
        Args:
            key: Redis key
            
        Returns:
            String value if key exists, None otherwise
        """
        try:
            result = await self.r.get(key)
            if result is None:
                logger.debug("redis_get_missing", key=key)
            else:
                logger.debug("redis_get", key=key)
            return result
        except Exception as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            raise

    async def delete(self, key: str) -> int:
        """
        Delete a key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            Number of keys deleted (0 or 1)
        """
        try:
            result = await self.r.delete(key)
            logger.debug("redis_delete", key=key, deleted=result)
            return result
        except Exception as e:
            logger.error("redis_delete_failed", key=key, error=str(e))
            raise

    async def set_json(self, key: str, data: dict, ex: int | None = None) -> bool:
        """
        Set a JSON-serializable dict in Redis.
        
        Args:
            key: Redis key
            data: Dictionary to serialize and store
            ex: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = json.dumps(data, ensure_ascii=False)
            result = await self.r.set(key, payload, ex=ex)
            logger.debug("redis_set_json", key=key, ex=ex)
            return bool(result)
        except Exception as e:
            logger.error("redis_set_json_failed", key=key, error=str(e))
            raise

    async def get_json(self, key: str) -> dict | None:
        """
        Get and parse a JSON value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Parsed dictionary if key exists and is valid JSON, None otherwise
        """
        try:
            raw = await self.r.get(key)
            if raw is None:
                logger.debug("redis_get_json_missing", key=key)
                return None
            
            try:
                result = json.loads(raw)
                logger.debug("redis_get_json", key=key)
                return result
            except json.JSONDecodeError as e:
                logger.warning("redis_get_json_invalid", key=key, error=str(e))
                return None
        except Exception as e:
            logger.error("redis_get_json_failed", key=key, error=str(e))
            raise

    def _lock_key(self, event_id: UUID) -> str:
        """
        Generate lock key for an event.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Lock key string
        """
        return f"analysis_lock:{event_id}"

    def _status_key(self, event_id: UUID) -> str:
        """
        Generate status key for an event.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Status key string
        """
        return f"analysis_status:{event_id}"

    async def acquire_lock(self, event_id: UUID, ttl: int = 300) -> bool:
        """
        Acquire a lock for an event.
        
        Args:
            event_id: Event UUID
            ttl: Lock expiration time in seconds (default: 300)
            
        Returns:
            True if lock was acquired, False if already locked
        """
        lock_key = self._lock_key(event_id)
        return await self.set_nx(lock_key, "1", ex=ttl)

    async def release_lock(self, event_id: UUID) -> None:
        """
        Release a lock for an event.
        
        Args:
            event_id: Event UUID
        """
        lock_key = self._lock_key(event_id)
        await self.delete(lock_key)

    async def set_status(self, event_id: UUID, status: str, ttl: int = 600) -> None:
        """
        Set status for an event.
        
        Args:
            event_id: Event UUID
            status: Status string to store
            ttl: Status expiration time in seconds (default: 600)
        """
        status_key = self._status_key(event_id)
        await self.set(status_key, status, ex=ttl)
