"""
Cache-first helper for catalog operations.
Implements Redis → DB fallback pattern with cache warming.
"""
from typing import List, Literal
from uuid import UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.schemas import SportDTO, CompetitionDTO
from app.infrastructure.cache.sports import SportsCache
from app.infrastructure.cache.competitions import CompetitionsCache
from app.infrastructure.repositories.sport import SportRepository
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.config import policy_loader

logger = structlog.get_logger()

PlanFilter = Literal["free", "pro", "all_available"]


class CatalogCacheHelper:
    """Helper for cache-first catalog operations."""

    def __init__(
        self,
        session: AsyncSession,
        sports_cache: SportsCache,
        competitions_cache: CompetitionsCache,
    ):
        self.session = session
        self.sports_cache = sports_cache
        self.competitions_cache = competitions_cache

    async def get_sports_catalog(self, plan: PlanFilter) -> List[SportDTO]:
        """
        Get sports catalog with cache-first strategy.

        Args:
            plan: Filter by plan type (free, pro, all_available)

        Returns:
            List of SportDTO filtered by plan
        """
        logger.info("get_sports_catalog_started", plan=plan)

        # Try cache first
        cached_data = await self.sports_cache.get_catalog()

        if cached_data and "sports" in cached_data:
            logger.info("sports_catalog_from_cache", count=len(cached_data["sports"]))
            sports_dtos = [SportDTO(**sport) for sport in cached_data["sports"]]
        else:
            # Fallback to DB
            logger.info("sports_catalog_cache_miss_fetching_from_db")
            sport_repo = SportRepository(self.session)
            sports = await sport_repo.get_all()

            # Convert to DTOs
            sports_dtos = [
                SportDTO(
                    id=sport.id,
                    category=sport.category,
                    plan_visibility=sport.plan_visibility,
                    is_active=sport.is_active,
                )
                for sport in sports
            ]

            # Warm the cache
            cache_data = {
                "sports": [dto.model_dump() for dto in sports_dtos],
                "updated_at": str(sports[0].created_at) if sports else None,
            }
            await self.sports_cache.set_catalog(cache_data)
            logger.info("sports_catalog_cache_warmed", count=len(sports_dtos))

        # Filter by plan
        filtered = self._filter_sports_by_plan(sports_dtos, plan)
        logger.info("sports_catalog_filtered", plan=plan, total=len(sports_dtos), filtered=len(filtered))

        return filtered

    async def get_competitions_catalog(
        self, category: str, plan: PlanFilter
    ) -> List[CompetitionDTO]:
        """
        Get competitions catalog with cache-first strategy.

        Args:
            category: Sport category (e.g., 'soccer')
            plan: Filter by plan type (free, pro, all_available)

        Returns:
            List of CompetitionDTO filtered by plan
        """
        logger.info("get_competitions_catalog_started", category=category, plan=plan)

        # Try cache first
        cached_data = await self.competitions_cache.get_catalog(category)

        if cached_data and "competitions" in cached_data:
            logger.info("competitions_catalog_from_cache", category=category, count=len(cached_data["competitions"]))
            competitions_dtos = [CompetitionDTO(**comp) for comp in cached_data["competitions"]]
        else:
            # Fallback to DB
            logger.info("competitions_catalog_cache_miss_fetching_from_db", category=category)

            # Get sport_id for category
            sport_repo = SportRepository(self.session)
            sport = await sport_repo.get_by_category(category)

            if not sport:
                logger.warning("sport_not_found_for_category", category=category)
                return []

            # Get competitions for this sport
            comp_repo = CompetitionsRepository(self.session)
            competitions = await comp_repo.get_active_by_sport(sport.id)

            # Convert to DTOs
            competitions_dtos = [
                CompetitionDTO(
                    id=comp.id,
                    sport_id=comp.sport_id,
                    title=comp.title,
                    provider=comp.provider,
                    provider_key=comp.provider_key,
                    plan_visibility=comp.plan_visibility,
                    is_active=comp.is_active,
                )
                for comp in competitions
            ]

            # Warm the cache
            cache_data = {
                "competitions": [dto.model_dump() for dto in competitions_dtos],
                "updated_at": str(competitions[0].created_at) if competitions else None,
            }
            await self.competitions_cache.set_catalog(category, cache_data)
            logger.info("competitions_catalog_cache_warmed", category=category, count=len(competitions_dtos))

        # Filter by plan
        filtered = self._filter_competitions_by_plan(competitions_dtos, plan)
        logger.info("competitions_catalog_filtered", category=category, plan=plan, total=len(competitions_dtos), filtered=len(filtered))

        return filtered

    def _filter_sports_by_plan(self, sports: List[SportDTO], plan: PlanFilter) -> List[SportDTO]:
        """Filter sports by plan using policy loader."""
        if plan == "all_available":
            return [s for s in sports if s.plan_visibility != "unavailable"]

        # Get the list of categories for this plan from policy
        result = []
        for sport in sports:
            visibility = policy_loader.get_visibility_for_category("odds_api", sport.category)

            # Exclude unavailable
            if visibility == "unavailable":
                continue

            # Filter by requested plan
            if plan == "free" and visibility == "free":
                result.append(sport)
            elif plan == "pro" and visibility in ["free", "pro"]:
                result.append(sport)

        return result

    def _filter_competitions_by_plan(
        self, competitions: List[CompetitionDTO], plan: PlanFilter
    ) -> List[CompetitionDTO]:
        """Filter competitions by plan using policy loader."""
        if plan == "all_available":
            return [c for c in competitions if c.plan_visibility != "unavailable"]

        # Get the list of competitions for this plan from policy
        result = []
        for comp in competitions:
            visibility = policy_loader.get_visibility_for_competition("odds_api", comp.provider_key)

            # Exclude unavailable
            if visibility == "unavailable":
                continue

            # Filter by requested plan
            if plan == "free" and visibility == "free":
                result.append(comp)
            elif plan == "pro" and visibility in ["free", "pro"]:
                result.append(comp)

        return result
