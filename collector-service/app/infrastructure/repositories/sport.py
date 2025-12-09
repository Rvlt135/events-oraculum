from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import structlog

from app.domain.entities.data_layer.sport_dto import SportDTO
from app.infrastructure.db.orm.data_layer.sports import Sport
from app.infrastructure.repositories.base import BaseRepository
from app.utils.time_utils import now_utc

logger = structlog.get_logger()


class SportRepository(BaseRepository[Sport]):
    def __init__(self, session: AsyncSession):
        super().__init__(Sport, session)

    async def get_or_create(self, category: str, plan_visibility: str, provider: str) -> UUID:
        result = await self.session.execute(
            select(Sport).where(Sport.category == category, Sport.provider == provider)
        )
        sport = result.scalar_one_or_none()

        if not sport:
            sport = Sport(
                category=category,
                provider=provider,
                is_active=True,
                plan_visibility=plan_visibility
            )
            sport = await self.create(sport)
            logger.info("sport_created", category=category, id=str(sport.id), plan_visibility=plan_visibility)
        else:
            if sport.plan_visibility != plan_visibility:
                sport.plan_visibility = plan_visibility
                await self.session.flush()
                logger.info("sport_plan_visibility_updated", category=category, id=str(sport.id), plan_visibility=plan_visibility)

        return sport.id

    async def get_by_category(self, category: str) -> Optional[Sport]:
        result = await self.session.execute(
            select(Sport).where(Sport.category == category)
        )
        return result.scalar_one_or_none()

    async def deactivate(self, sport_id: UUID) -> None:
        sport = await self.get_by_id(sport_id)
        if sport:
            sport.is_active = False
            await self.session.flush()
            logger.info("sport_deactivated", id=str(sport_id))


    # TODO: New
    async def bulk_upsert(self, sports: list[SportDTO]) -> list[Sport]:
        """
        Bulk upsert sports by unique key (provider, category).
        
        Performs INSERT ... ON CONFLICT DO UPDATE for multiple sports records.
        Updates only mutable fields: is_active, plan_visibility, updated_at.
        
        Args:
            sports: List of SportDTO to upsert
            
        Returns:
            List of Sport ORM models with actual id values assigned by DB
        """
        if not sports:
            logger.debug("bulk_upsert_sports_empty_input")
            return []
        
        try:
            logger.info("bulk_upsert_sports_started", count=len(sports))
            
            # Build insert values from DTOs
            values = []
            for sport_dto in sports:
                values.append({
                    "provider": sport_dto.provider,
                    "category": sport_dto.category,
                    "is_active": sport_dto.is_active,
                    "plan_visibility": sport_dto.plan_visibility,
                })
            
            # Build INSERT ... ON CONFLICT DO UPDATE statement
            stmt = insert(Sport).values(values)
            
            stmt = stmt.on_conflict_do_update(
                constraint="uq_sports_provider_category",
                set_={
                    "is_active": stmt.excluded.is_active,
                    "plan_visibility": stmt.excluded.plan_visibility,
                    "updated_at": now_utc(),
                }
            ).returning(Sport)
            
            # Execute and fetch results
            result = await self.session.execute(stmt)
            await self.session.flush()
            
            upserted_sports = list(result.scalars().all())
            
            logger.debug(
                "bulk_upsert_sports_completed",
                input_count=len(sports),
                upserted_count=len(upserted_sports),
            )
            
            return upserted_sports
            
        except Exception as e:
            logger.error(
                "bulk_upsert_sports_failed",
                error=str(e),
                count=len(sports) if sports else 0,
                exc_info=True,
            )
            raise
