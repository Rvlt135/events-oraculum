"""
Cache helper for catalog operations.
Handles only cache reads - DB fallback is handled at service layer.
"""
from typing import List, Literal, Optional
import structlog

from app.api.schemas.schemas import SportDTO, CompetitionDTO
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.competitions import CompetitionsCache

logger = structlog.get_logger()

PlanFilter = Literal["free", "pro", "all_available"]


class CatalogCacheHelper:
    """Helper for catalog cache operations."""

    def __init__(
        self,
        sports_cache: SportsCache,
        competitions_cache: CompetitionsCache,
    ):
        self.sports_cache = sports_cache
        self.competitions_cache = competitions_cache

    async def get_sports_from_cache(self, plan: PlanFilter) -> Optional[List[SportDTO]]:
        """
        Get sports catalog from cache only.

        Args:
            plan: Filter by plan type (free, pro, all_available)

        Returns:
            List of SportDTO filtered by plan, or None if cache miss
        """
        logger.info("get_sports_from_cache_started", plan=plan)

        # Try cache
        cached_data = await self.sports_cache.get_catalog()

        if not cached_data or "sports" not in cached_data:
            logger.info("sports_catalog_cache_miss")
            return None

        logger.info("sports_catalog_from_cache", count=len(cached_data["sports"]))
        sports_dtos = [SportDTO(**sport) for sport in cached_data["sports"]]

        # Filter by plan
        filtered = self.filter_sports_by_plan(sports_dtos, plan)
        logger.info("sports_catalog_filtered", plan=plan, total=len(sports_dtos), filtered=len(filtered))

        return filtered

    async def get_competitions_from_cache(
        self, category: str, plan: PlanFilter
    ) -> Optional[List[CompetitionDTO]]:
        """
        Get competitions catalog from cache only.

        Args:
            category: Sport category (e.g., 'soccer')
            plan: Filter by plan type (free, pro, all_available)

        Returns:
            List of CompetitionDTO filtered by plan, or None if cache miss
        """
        logger.info("get_competitions_from_cache_started", category=category, plan=plan)

        # Try cache
        cached_data = await self.competitions_cache.get_catalog(category)

        if not cached_data or "competitions" not in cached_data:
            logger.info("competitions_catalog_cache_miss", category=category)
            return None

        logger.info("competitions_catalog_from_cache", category=category, count=len(cached_data["competitions"]))
        competitions_dtos = [CompetitionDTO(**comp) for comp in cached_data["competitions"]]

        # Filter by plan
        filtered = self.filter_competitions_by_plan(competitions_dtos, plan)
        logger.info("competitions_catalog_filtered", category=category, plan=plan, total=len(competitions_dtos), filtered=len(filtered))

        return filtered

    async def warm_sports_cache(self, sports_dtos: List[SportDTO]) -> None:
        """
        Warm sports cache with provided DTOs.

        Args:
            sports_dtos: List of SportDTO to cache
        """
        cache_data = {
            "sports": [dto.model_dump(mode="json") for dto in sports_dtos],
            "updated_at": None,
        }
        await self.sports_cache.set_catalog(cache_data)
        logger.info("sports_cache_warmed", count=len(sports_dtos))

    async def warm_competitions_cache(self, category: str, competitions_dtos: List[CompetitionDTO]) -> None:
        """
        Warm competitions cache with provided DTOs.

        Args:
            category: Sport category
            competitions_dtos: List of CompetitionDTO to cache
        """
        cache_data = {
            "competitions": [dto.model_dump(mode="json") for dto in competitions_dtos],
            "updated_at": None,
        }
        await self.competitions_cache.set_catalog(category, cache_data)
        logger.info("competitions_cache_warmed", category=category, count=len(competitions_dtos))

    def filter_sports_by_plan(self, sports: List[SportDTO], plan: PlanFilter) -> List[SportDTO]:
        """
        Filter sports by plan using plan_visibility from DTO.
        
        - free: Only sports with plan_visibility == "free"
        - pro: Only sports with plan_visibility == "pro"
        - all_available: All sports except unavailable
        """
        if plan == "all_available":
            return [s for s in sports if s.plan_visibility != "unavailable"]

        # Filter by plan_visibility directly from DTO (optimized, no policy_loader calls)
        if plan == "free":
            return [s for s in sports if s.plan_visibility == "free"]
        elif plan == "pro":
            return [s for s in sports if s.plan_visibility == "pro"]

        return []

    def filter_competitions_by_plan(
        self, competitions: List[CompetitionDTO], plan: PlanFilter
    ) -> List[CompetitionDTO]:
        """
        Filter competitions by plan using plan_visibility from DTO.
        
        - free: Only competitions with plan_visibility == "free"
        - pro: Only competitions with plan_visibility == "pro"
        - all_available: All competitions except unavailable
        """
        if plan == "all_available":
            return [c for c in competitions if c.plan_visibility != "unavailable"]

        # Filter by plan_visibility directly from DTO (optimized, no policy_loader calls)
        if plan == "free":
            return [c for c in competitions if c.plan_visibility == "free"]
        elif plan == "pro":
            return [c for c in competitions if c.plan_visibility == "pro"]

        return []
