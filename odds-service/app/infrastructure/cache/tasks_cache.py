"""
Events cache for storing upcoming events per competition with atomic updates.
"""
import asyncio
from typing import Optional, Literal
import structlog
from redis.asyncio import Redis
import secrets

from app.domain.entities.event import EventDTO

logger = structlog.get_logger()


class TasksCache:
    """Cache for tasks broker"""

    def __init__(self, redis_client: Redis, rate_limit_qps: int):
        self.redis = redis_client
        self._rate_limit_qps = rate_limit_qps

    def get_keys_prefix(self, key_cache: Literal[
            'job_prefix',
            'lock_prefix',
            'lock_script',
            'llm_qps'
        ]
    ) -> str:
        keys = {"job_prefix": "job:prioritize:{provider_key}:{run_id}",
                "lock_prefix": "lock:prioritize:{provider_key}",
                "lock_script": "lock:prioritize:{provider_key}",
                "llm_qps": "llm:qps:{model}"
                }.get(key_cache)
        return keys

    async def check_idempotency(self, provider_key: str, run_id: str) -> bool:
        """
        Check if this provider_key was already processed in this run (idempotency).

        Args:
            provider_key: Competition provider_key
            run_id: Unique run identifier

        Returns:
            True if already processed (should skip), False if can proceed
        """
        key = self.get_keys_prefix("job_prefix").format(provider_key=provider_key, run_id=run_id)
        try:
            # SET with NX (only if not exists) and EX (expire in 900 seconds)
            result = await self.redis.set(key, "1", nx=True, ex=900)
            if not result:
                logger.info("idempotency_skip_already_processed", provider_key=provider_key, run_id=run_id)
                return True
            return False
        except Exception as e:
            logger.error("idempotency_check_failed", provider_key=provider_key, error=str(e))
            # On error, allow processing to continue
            return False

    async def acquire_lock(self, provider_key: str) -> Optional[str]:
        """
        Acquire execution lock for provider_key (optional).

        Args:
            provider_key: Competition provider_key

        Returns:
            Lock token if acquired, None if already locked
        """
        token = secrets.token_hex(16)
        key = self.get_keys_prefix("lock_prefix").format(provider_key=provider_key)
        try:
            # SET with NX (only if not exists) and PX (expire in 60000 milliseconds)
            result = await self.redis.set(key, token, nx=True, px=60000)
            if not result:
                logger.info("lock_not_acquired_already_locked", provider_key=provider_key)
                return None
            logger.debug("lock_acquired", provider_key=provider_key, token=token[:8])
            return token
        except Exception as e:
            logger.error("lock_acquisition_failed", provider_key=provider_key, error=str(e))
            return None

    async def release_lock(self, provider_key: str, token: str) -> None:
        """
        Release execution lock using compare-and-delete.

        Args:
            provider_key: Competition provider_key
            token: Lock token from acquire_lock
        """
        key = self.get_keys_prefix("lock_script").format(provider_key=provider_key)
        try:
            # Lua script for atomic compare-and-delete
            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = await self.redis.eval(script, 1, key, token)
            if result:
                logger.debug("lock_released", provider_key=provider_key, token=token[:8])
            else:
                logger.warning("lock_release_failed_token_mismatch", provider_key=provider_key)
        except Exception as e:
            logger.error("lock_release_failed", provider_key=provider_key, error=str(e))

    async def check_qps_limit(self, model: str) -> None:
        """
        Check and enforce QPS limit for LLM model (soft limit with retry).

        Args:
            model: LLM model name
        """
        key = self.get_keys_prefix("llm_qps").format(model=model)
        try:
            # INCR and EXPIRE in pipeline for atomicity
            pipe = self.redis.pipeline()
            await pipe.incr(key)
            await pipe.expire(key, 1)
            results = await pipe.execute()
            current_qps = results[0] if results else 0

            if current_qps > self._rate_limit_qps:
                logger.warning(
                    "qps_limit_exceeded",
                    model=model,
                    current_qps=current_qps,
                    limit=self._rate_limit_qps
                )
                # Soft limit: sleep 50ms and retry
                await asyncio.sleep(0.05)
                # Retry check
                current_qps_str = await self.redis.get(key)
                if current_qps_str and int(current_qps_str) > self._rate_limit_qps:
                    await asyncio.sleep(0.05)
        except Exception as e:
            logger.error("qps_check_failed", model=model, error=str(e))
            # On error, allow processing to continue
