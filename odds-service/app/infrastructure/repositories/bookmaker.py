from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.bookmakers import Bookmaker
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class BookmakerRepository(BaseRepository[Bookmaker]):
    def __init__(self, session: AsyncSession):
        super().__init__(Bookmaker, session)

    async def get_or_create_by_key(self, key: str, name: str, region: str) -> UUID:
        """
        Get or create bookmaker by key (idempotent).

        Key: (key) - unique constraint on key field.

        Args:
            key: Bookmaker key (unique identifier)
            name: Bookmaker name
            region: Bookmaker region

        Returns:
            UUID of existing or newly created bookmaker
        """
        result = await self.session.execute(
            select(Bookmaker).where(Bookmaker.key == key)
        )
        bookmaker = result.scalar_one_or_none()

        if not bookmaker:
            bookmaker = Bookmaker(
                key=key,
                name=name,
                region=region,
                is_active=True
            )
            bookmaker = await self.create(bookmaker)
            logger.info("bookmaker_created", key=key, name=name, region=region, id=str(bookmaker.id))
        else:
            updated = False
            if bookmaker.name != name:
                bookmaker.name = name
                updated = True
            if bookmaker.region != region:
                bookmaker.region = region
                updated = True
            if updated:
                await self.session.flush()
                logger.debug("bookmaker_updated", key=key, new_name=name, new_region=region)

        return bookmaker.id

    async def get_or_create(self, key: str, name: str, region: str) -> UUID:
        """Deprecated: Use get_or_create_by_key instead."""
        return await self.get_or_create_by_key(key, name, region)

    async def get_by_key(self, key: str) -> Optional[Bookmaker]:
        result = await self.session.execute(
            select(Bookmaker).where(Bookmaker.key == key)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> List[Bookmaker]:
        result = await self.session.execute(
            select(Bookmaker).where(Bookmaker.is_active == True)
        )
        return list(result.scalars().all())

    async def deactivate(self, bookmaker_id: UUID) -> None:
        bookmaker = await self.get_by_id(bookmaker_id)
        if bookmaker:
            bookmaker.is_active = False
            await self.session.flush()
            logger.info("bookmaker_deactivated", id=str(bookmaker_id))
