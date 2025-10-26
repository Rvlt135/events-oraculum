from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infra.redis_client import RedisManager

logger = structlog.get_logger()


class UnitOfWork:
    """
    Unit of Work pattern for managing database transactions.

    Provides explicit transaction boundaries with automatic rollback on errors.
    Use as async context manager for atomic operations.

    Example:
        async with UnitOfWork(session, redis) as uow:
            await repository.create(entity)
            await uow.commit()
    """

    def __init__(self, session: AsyncSession, redis: Optional[RedisManager] = None):
        self.session = session
        self.redis = redis
        self._transaction = None
        self._committed = False

    async def __aenter__(self) -> "UnitOfWork":
        """Begin transaction."""
        if not self.session.in_transaction():
            self._transaction = await self.session.begin()
            logger.debug("transaction_started")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback transaction based on exceptions."""
        if exc_type is not None:
            await self.rollback()
            logger.debug("transaction_rolled_back", exc_type=exc_type.__name__)
            return False

        if not self._committed and self._transaction:
            await self.commit()

        return False

    async def commit(self) -> None:
        """Explicitly commit the transaction."""
        if self._transaction and not self._committed:
            await self.session.commit()
            self._committed = True
            logger.debug("transaction_committed")

    async def rollback(self) -> None:
        """Explicitly rollback the transaction."""
        if self._transaction and not self._committed:
            await self.session.rollback()
            logger.debug("transaction_rolled_back_explicit")

    async def flush(self) -> None:
        """Flush changes without committing."""
        await self.session.flush()
        logger.debug("session_flushed")
