from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.orm_models import Bookmaker
from .base import BaseRepository

logger = structlog.get_logger()


class BookmakerRepository(BaseRepository[Bookmaker]):
    def __init__(self, session: AsyncSession):
        super().__init__(Bookmaker, session)

    async def get_or_create(self, key: str, name: str, region: str) -> UUID:
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
            logger.info("bookmaker_created", key=key, name=name, id=str(bookmaker.id))
        else:
            if bookmaker.name != name:
                bookmaker.name = name
                await self.session.flush()
                logger.debug("bookmaker_updated", key=key, new_name=name)

        return bookmaker.id

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
