from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import structlog

from app.domain.entities import CompetitionEntity
from app.infrastructure.db.orm.competition import Competition
from app.infrastructure.repositories.base import BaseRepository
from app.utils.time_utils import now_utc

logger = structlog.get_logger()


class CompetitionsRepository(BaseRepository[Competition]):
    def __init__(self, session: AsyncSession):
        super().__init__(Competition, session)

    async def get_or_create(
        self,
        sport_id: UUID,
        slug_key: str,
        title: str,
        description: str = None,
        plan_visibility: str = "free",
        provider: str = "odds_api",
        api_sources: Optional[Dict[str, Any]] = None
    ) -> UUID:
        result = await self.session.execute(
            select(Competition).where(
                Competition.slug_key == slug_key,
                Competition.provider == provider
            )
        )
        competition = result.scalar_one_or_none()

        if not competition:
            api_sources_dict = api_sources or {}
            competition = Competition(
                sport_id=sport_id,
                provider=provider,
                slug_key=slug_key,
                title=title,
                description=description,
                is_active=True,
                plan_visibility=plan_visibility,
                api_sources=api_sources_dict
            )
            competition = await self.create(competition)
            logger.info("competition_created", key=slug_key, title=title, id=str(competition.id), plan_visibility=plan_visibility)
        else:
            updated = False
            if competition.title != title:
                competition.title = title
                updated = True
            if description and competition.description != description:
                competition.description = description
                updated = True
            if competition.plan_visibility != plan_visibility:
                competition.plan_visibility = plan_visibility
                updated = True
                logger.info("competition_plan_visibility_updated", key=slug_key, id=str(competition.id), plan_visibility=plan_visibility)
            
            if api_sources:
                current_api_sources = competition.api_sources or {}
                api_sources_updated = False
                for key, value in api_sources.items():
                    if current_api_sources.get(key) != value:
                        current_api_sources[key] = value
                        api_sources_updated = True
                if api_sources_updated:
                    competition.api_sources = current_api_sources
                    updated = True

            if updated:
                await self.session.flush()
                logger.info("competition_updated", key=slug_key, new_title=title)

        return competition.id

    async def get_by_key(self, key: str) -> Optional[Competition]:
        result = await self.session.execute(
            select(Competition).where(Competition.slug_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_slug_key(self, provider: str, slug_key: str) -> Optional[Competition]:
        """Get competition by provider and slug_key."""
        result = await self.session.execute(
            select(Competition).where(
                Competition.provider == provider,
                Competition.slug_key == slug_key
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_sport(self, sport_id: UUID) -> List[Competition]:
        result = await self.session.execute(
            select(Competition)
            .where(Competition.sport_id == sport_id)
            .where(Competition.is_active == True)
        )
        return list(result.scalars().all())

    async def deactivate(self, competition_id: UUID) -> None:
        competition = await self.get_by_id(competition_id)
        if competition:
            competition.is_active = False
            await self.session.flush()
            logger.info("competition_deactivated", id=str(competition_id))

    async def get_all_by_provider(self, provider: str) -> List[Competition]:
        """Get all active competitions for a provider."""
        result = await self.session.execute(
            select(Competition).where(
                Competition.provider == provider,
                Competition.is_active == True
            )
        )
        return list(result.scalars().all())

    # TODO: New
    async def bulk_upsert(self, competitions: list[CompetitionEntity]) -> list[Competition]:
        """
        Bulk upsert competitions by unique key (provider, slug_key).
        
        Performs INSERT ... ON CONFLICT DO UPDATE for multiple competition records.
        Updates only mutable fields: title, plan_visibility, is_active, api_sources, updated_at.
        
        Args:
            competitions: List of CompetitionEntity to upsert (sport_id must be set)
            
        Returns:
            List of Competition ORM models with actual id and sport_id values assigned by DB
        """
        if not competitions:
            logger.debug("bulk_upsert_competitions_empty_input")
            return []
        
        try:
            logger.info("bulk_upsert_competitions_started", count=len(competitions))
            
            # Build insert values from CompetitionEntity
            values = []
            for comp_entity in competitions:
                values.append({
                    "provider": comp_entity.provider,
                    "slug_key": comp_entity.slug_key,
                    "sport_id": comp_entity.sport_id,
                    "title": comp_entity.title,
                    "plan_visibility": comp_entity.plan_visibility,
                    "is_active": comp_entity.is_active,
                    "api_sources": comp_entity.api_sources or {},
                })
            
            # Build INSERT ... ON CONFLICT DO UPDATE statement
            stmt = insert(Competition).values(values)
            
            stmt = stmt.on_conflict_do_update(
                constraint="uq_competitions_slug_key",
                set_={
                    "title": stmt.excluded.title,
                    "plan_visibility": stmt.excluded.plan_visibility,
                    "is_active": stmt.excluded.is_active,
                    "api_sources": stmt.excluded.api_sources,
                    "updated_at": now_utc(),
                }
            ).returning(Competition)
            
            # Execute and fetch results
            result = await self.session.execute(stmt)
            await self.session.flush()
            
            upserted_competitions = list(result.scalars().all())
            
            logger.debug(
                "bulk_upsert_competitions_completed",
                input_count=len(competitions),
                upserted_count=len(upserted_competitions),
            )
            
            logger.info("bulk_upsert_competitions_success", count=len(upserted_competitions))
            
            return upserted_competitions
            
        except Exception as e:
            logger.error(
                "bulk_upsert_competitions_failed",
                error=str(e),
                count=len(competitions) if competitions else 0,
                exc_info=True,
            )
            raise
