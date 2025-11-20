"""
Event priority repository for managing priority scores.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import structlog

from app.infrastructure.db.orm.event_priorities import EventPriority
from app.infrastructure.repositories.base import BaseRepository
from app.utils.time_utils import now_utc

logger = structlog.get_logger()


class EventPriorityRepository(BaseRepository[EventPriority]):
    def __init__(self, session: AsyncSession):
        super().__init__(EventPriority, session)

    async def upsert_batch(
        self,
        provider: str,
        slug_key: str,
        priorities: List[dict],
        model: str,
    ) -> int:
        """
        Upsert event priorities in batch.

        Args:
            provider: Provider name
            slug_key: Provider key
            priorities: List of {event_id, score} dicts
            model: Model used for scoring

        Returns:
            Number of records upserted
        """
        if not priorities:
            return 0

        now = now_utc()

        values = []
        for item in priorities:
            values.append({
                "provider": provider,
                "slug_key": slug_key,
                "event_id": UUID(item["event_id"]) if isinstance(item["event_id"], str) else item["event_id"],
                "priority": float(item["priority"]),
                "model": model,
                "evaluated_at": now,
                "meta": {},
            })

        stmt = pg_insert(EventPriority).values(values)

        stmt = stmt.on_conflict_do_update(
            constraint="uq_event_priorities_slug_key_event_id",
            set_={
                "priority": stmt.excluded.priority,
                "model": stmt.excluded.model,
                "evaluated_at": stmt.excluded.evaluated_at,
                "meta": stmt.excluded.meta,
            }
        )

        await self.session.execute(stmt)

        logger.info(
            "event_priorities_upserted",
            slug_key=slug_key,
            count=len(values),
            model=model
        )

        return len(values)

    async def get_by_slug_key(
        self,
        slug_key: str,
        limit: int = 1000
    ) -> List[EventPriority]:
        """
        Get priorities for provider key, ordered by priority DESC.

        Args:
            slug_key: Provider key
            limit: Max records

        Returns:
            List of EventPriority
        """
        result = await self.session.execute(
            select(EventPriority)
            .where(EventPriority.slug_key == slug_key)
            .order_by(EventPriority.priority.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
