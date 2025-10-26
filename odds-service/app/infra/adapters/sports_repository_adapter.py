"""
Adapter for SportsRepository port implementation.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.sports_repository import SportsRepository
from app.infra.repositories.sport import SportRepository as ConcreteSportRepository


class SportsRepositoryAdapter(SportsRepository):
    """Adapter for concrete SportRepository to implement SportsRepository port."""

    def __init__(self, session: AsyncSession):
        self._concrete_repo = ConcreteSportRepository(session)

    async def get_by_key(self, key: str) -> Optional[UUID]:
        """Get sport ID by key."""
        sport = await self._concrete_repo.get_by_name(key)
        return sport.id if sport else None

    async def upsert(self, key: str, name: str) -> UUID:
        """Upsert sport by key."""
        return await self._concrete_repo.get_or_create(key, name)

    async def get_all(self) -> list:
        """Get all sports."""
        return await self._concrete_repo.get_all()
