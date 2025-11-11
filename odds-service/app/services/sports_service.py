"""
Sports service for managing sports data synchronization.
"""
from typing import Dict, Any, List, Literal
import structlog
from prometheus_client import Counter, Histogram
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid import UUID

from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.repositories.sport import SportRepository
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.config import policy_loader
from app.domain.entities.sport import SportEntity
from app.domain.entities.competition import CompetitionEntity
from app.api.schemas.schemas import SportDTO, CompetitionDTO
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper

logger = structlog.get_logger()

# Metrics
sports_sync_duration = Histogram("sports_sync_duration_seconds", "Time spent syncing sports data")
sports_synced_total = Counter("sports_synced_total", "Total number of sports synced")
sports_sync_errors_total = Counter("sports_sync_errors_total", "Total number of sports sync errors")


class SportsService:
    """Service for managing sports data synchronization."""

    def __init__(
        self,
        odds_client: OddsAPIClient,
        session_factory: async_sessionmaker[AsyncSession],
        sports_cache: SportsCache,
        competitions_cache: CompetitionsCache,
        catalog_cache_helper: CatalogCacheHelper,
    ):
        self._odds_client = odds_client
        self._session_factory = session_factory
        self._sports_cache = sports_cache
        self._competitions_cache = competitions_cache
        self._catalog_cache_helper = catalog_cache_helper


    async def sync_sports_categories(self, resp: List[Dict[str, Any]]) -> dict:
        """
        Extract unique sport categories (from 'group') and upsert them into the sports table.
        
        Returns:
            Dict with sync results for categories
        """
        logger.info("sports_categories_sync_started")
        
        try:
            # Fetch sports data from external provider
            logger.info("sports_data_fetched", count=len(resp))
            
            # Extract unique categories (groups) and normalize (replace spaces with underscores)
            unique_categories = set()
            for item in resp:
                group = item.get("group", "").lower().strip()
                if group:
                    # Normalize category: replace spaces with underscores
                    normalized_category = group.replace(" ", "_")
                    unique_categories.add(normalized_category)
            
            logger.info("unique_categories_extracted", count=len(unique_categories))
            
            # Create session and upsert categories
            synced_count = 0
            async with self._session_factory() as session:
                async with session.begin():
                    sport_repository = SportRepository(session)
                    
                    for category in sorted(unique_categories):
                        try:
                            plan_visibility = policy_loader.get_visibility_for_category("odds_api", category)
                            await sport_repository.get_or_create(category, plan_visibility=plan_visibility, provider="odds_api")
                            synced_count += 1
                        except Exception as e:
                            logger.error("sport_category_upsert_failed", category=category, error=str(e))
                            sports_sync_errors_total.inc()
                    
                    logger.info("sports_categories_batch_committed", count=synced_count)
            
            sports_synced_total.inc(synced_count)
            
            result = {
                "status": "success",
                "synced_count": synced_count,
                "total_categories": len(unique_categories),
            }
            
            logger.info("sports_categories_sync_completed", **result)
            return result
            
        except Exception as e:
            logger.error("sports_categories_sync_failed", error=str(e))
            sports_sync_errors_total.inc()
            return {
                "status": "error",
                "message": str(e),
                "synced_count": 0,
            }

    async def sync_competitions(self, resp: List[Dict[str, Any]]) -> dict:
        """
        Upsert competitions from /v4/sports and link them with sport_id from the corresponding category.
        
        Returns:
            Dict with sync results for competitions
        """
        logger.info("competitions_sync_started")
        
        try:
            # Fetch sports data from external provider
            logger.info("sports_data_fetched", count=len(resp))
            
            # Get category -> sport_id mapping using a separate read-only session
            async with self._session_factory() as read_session:
                category_to_sport_id = await self._get_category_to_sport_id_mapping(read_session)
            
            # Create session and upsert competitions
            synced_count = 0
            async with self._session_factory() as session:
                async with session.begin():
                    competitions_repository = CompetitionsRepository(session)
                    
                    for item in resp:
                        try:
                            provider_key = item.get("key", "").strip()
                            title = item.get("title", "")
                            description = item.get("description", "")
                            category = item.get("group", "").lower().strip()
                            # Normalize category: replace spaces with underscores
                            normalized_category = category.replace(" ", "_")
                            is_active = item.get("active", True)
                            
                            if not provider_key or not normalized_category:
                                logger.warning("invalid_competition_data", data=item)
                                continue
                            
                            # Get sport_id for this category (use normalized category)
                            sport_id = category_to_sport_id.get(normalized_category)
                            if not sport_id:
                                logger.warning("sport_not_found_for_category", category=normalized_category)
                                continue
                            
                            # Get plan visibility from policy
                            plan_visibility = policy_loader.get_visibility_for_competition("odds_api", provider_key)

                            # Upsert competition
                            await competitions_repository.get_or_create(
                                sport_id=sport_id,
                                provider_key=provider_key,
                                title=title,
                                description=description if description else None,
                                plan_visibility=plan_visibility,
                                provider="odds_api"
                            )
                            
                            synced_count += 1
                            
                        except Exception as e:
                            logger.error("competition_upsert_failed", item=item, error=str(e))
                            sports_sync_errors_total.inc()
                    
                    logger.info("competitions_batch_committed", count=synced_count)
            
            result = {
                "status": "success",
                "synced_count": synced_count,
                "total_fetched": len(resp),
            }
            
            logger.info("competitions_sync_completed", **result)
            return result
            
        except Exception as e:
            logger.error("competitions_sync_failed", error=str(e))
            sports_sync_errors_total.inc()
            return {
                "status": "error",
                "message": str(e),
                "synced_count": 0,
            }

    async def _get_category_to_sport_id_mapping(self, session) -> Dict[str, UUID]:
        """Build a mapping of category -> sport_id using provided session."""
        category_to_sport_id = {}
        sport_repository = SportRepository(session)
        all_sports = await sport_repository.get_all()
        
        for sport in all_sports:
            category_to_sport_id[sport.category] = sport.id
        
        return category_to_sport_id

    async def sync_sports_and_competitions(self) -> Dict[str, Any]:
        """
        Composite method that runs both syncs sequentially and updates Redis cache.
        
        Returns:
            Composite sync result with counts and status
        """
        logger.info("sports_and_competitions_sync_started")
        
        try:
            with sports_sync_duration.time():
                # Step 1: Sync sport categories
                resp_raw_data = await self._odds_client.get_sports()
                categories_result = await self.sync_sports_categories(resp_raw_data)
                
                # Step 2: Sync competitions
                competitions_result = await self.sync_competitions(resp_raw_data)
                
                # Step 3: Update Redis cache
                try:
                    if not self._sports_cache:
                        logger.warning("sports_cache_not_initialized")
                    if not self._competitions_cache:
                        logger.warning("competitions_cache_not_initialized")
                    
                    async with self._session_factory() as session:
                        sport_repository = SportRepository(session)
                        sports = await sport_repository.get_all()
                        
                        if not sports:
                            logger.warning("no_sports_found_for_cache")
                        else:
                            # Use domain entities for cache serialization
                            sports_entities = [
                                SportEntity(
                                    id=sport.id,
                                    category=sport.category,
                                    is_active=sport.is_active,
                                    plan_visibility=sport.plan_visibility,
                                )
                                for sport in sports
                            ]
                            
                            cache_data = {
                                "sports": [entity.model_dump(mode="json") for entity in sports_entities],
                                "updated_at": str(sports[0].created_at) if sports else None,
                            }

                            # Set cache with TTL
                            if self._sports_cache:
                                await self._sports_cache.set_catalog(cache_data)
                                logger.info("sports_cache_updated", count=len(sports))
                            else:
                                logger.warning("sports_cache_skipped_not_initialized")

                            # Update competitions cache by category using domain entities
                            competitions_repo = CompetitionsRepository(session)
                            competitions_cached_count = 0
                            for sport in sports:
                                competitions = await competitions_repo.get_active_by_sport(sport.id)
                                competitions_entities = [
                                    CompetitionEntity(
                                        id=comp.id,
                                        sport_id=comp.sport_id,
                                        provider=comp.provider,
                                        provider_key=comp.provider_key,
                                        title=comp.title,
                                        plan_visibility=comp.plan_visibility,
                                        is_active=comp.is_active,
                                    )
                                    for comp in competitions
                                ]
                                
                                # Use model_dump to serialize entities - UUIDs will be converted to strings via field_serializer
                                comp_cache_data = {
                                    "competitions": [
                                        entity.model_dump(mode="json") 
                                        for entity in competitions_entities
                                    ],
                                    "updated_at": str(competitions[0].created_at) if competitions else None,
                                }
                                if self._competitions_cache:
                                    await self._competitions_cache.set_catalog(sport.category, comp_cache_data)
                                    competitions_cached_count += 1
                                    logger.info("competition_category_cached", category=sport.category, competitions_count=len(competitions))
                                else:
                                    logger.warning("competitions_cache_skipped_not_initialized", category=sport.category)

                            logger.info("competitions_cache_updated", categories_count=competitions_cached_count, total_sports=len(sports))

                except Exception as e:
                    logger.error("sports_cache_update_failed", error=str(e), exc_info=True)
            
            result = {
                "status": "success",
                "categories": categories_result,
                "competitions": competitions_result,
            }
            
            logger.info("sports_and_competitions_sync_completed", **result)
            return result
            
        except Exception as e:
            logger.error("sports_and_competitions_sync_failed", error=str(e))
            sports_sync_errors_total.inc()
            return {
                "status": "error",
                "message": str(e),
            }

    async def get_sports_catalog(self, plan: Literal["free", "pro", "all_available"]) -> List:
        """
        Get sports catalog with cache-first strategy and plan filtering.
        Uses CatalogCacheHelper for cache reads and Repository for DB fallback.

        Args:
            plan: Filter by plan type (free, pro, all_available)

        Returns:
            List of SportDTO filtered by plan
        """

        logger.info("get_sports_catalog_service", plan=plan)

        sports = await self._catalog_cache_helper.get_sports_from_cache(plan)

        if sports is not None:
            logger.info("sports_catalog_from_cache_service", plan=plan, count=len(sports))
            return sports

        # Cache miss - fallback to DB using repository
        logger.info("sports_catalog_cache_miss_using_db", plan=plan)
        async with self._session_factory() as session:
            sport_repo = SportRepository(session)
            sports_orm = await sport_repo.get_all()

            # Convert to DTOs
            sports_dtos = [
                SportDTO(
                    id=sport.id,
                    category=sport.category,
                    plan_visibility=sport.plan_visibility,
                    is_active=sport.is_active,
                )
                for sport in sports_orm
            ]

            # Filter by plan using helper
            filtered_sports = self._catalog_cache_helper.filter_sports_by_plan(sports_dtos, plan)

            # Warm the cache for next time
            await self._catalog_cache_helper.warm_sports_cache(sports_dtos)
            logger.info("sports_catalog_from_db_service", plan=plan, count=len(filtered_sports))

            return filtered_sports

    async def get_competitions_catalog(self, category: str, plan: Literal["free", "pro", "all_available"]) -> List:
        """
        Get competitions catalog with cache-first strategy and plan filtering.
        Uses CatalogCacheHelper for cache reads and Repository for DB fallback.

        Args:
            category: Sport category (e.g., 'soccer')
            plan: Filter by plan type (free, pro, all_available)

        Returns:
            List of CompetitionDTO filtered by plan
        """

        logger.info("get_competitions_catalog_service", category=category, plan=plan)


        competitions = await self._catalog_cache_helper.get_competitions_from_cache(category, plan)

        if competitions is not None:
            logger.info("competitions_catalog_from_cache_service", category=category, plan=plan, count=len(competitions))
            return competitions

        # Cache miss - fallback to DB using repository
        logger.info("competitions_catalog_cache_miss_using_db", category=category, plan=plan)
        async with self._session_factory() as session:
            # Get sport_id for category
            sport_repo = SportRepository(session)
            sport = await sport_repo.get_by_category(category)

            if not sport:
                logger.warning("sport_not_found_for_category", category=category)
                return []

            # Get competitions for this sport
            comp_repo = CompetitionsRepository(session)
            competitions_orm = await comp_repo.get_active_by_sport(sport.id)

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
                for comp in competitions_orm
            ]
            # com_dto = [comp.model_dump(mode="json") for comp in competitions_dtos]
            # Filter by plan using helper
            filtered_competitions = self._catalog_cache_helper.filter_competitions_by_plan(competitions_dtos, plan)

            # Warm the cache for next time
            await self._catalog_cache_helper.warm_competitions_cache(category, competitions_dtos)
            logger.info("competitions_catalog_from_db_service", category=category, plan=plan, count=len(filtered_competitions))

            return filtered_competitions
