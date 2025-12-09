"""
Sports service for managing sports data synchronization.
"""
from typing import Dict, Any, List, Literal
import structlog
from prometheus_client import Counter, Histogram
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid import UUID

from app.builders.data_layer.data_layer_builder import DataLayerBuilder
from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.repositories.sport import SportRepository
from app.infrastructure.cache.catalog.sports import SportsCache
from app.infrastructure.cache.catalog.competitions import CompetitionsCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.domain.entities.data_layer.sport import SportEntity
from app.domain.entities.data_layer.competition import CompetitionEntity, CompetitionReadDTO
from app.api.schemas.schemas import SportDTO, CompetitionDTO
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.domain.entities.data_layer.sport_dto import SportDTO, SportsAndCompetitionsDTO
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
        policy_loader: PolicyLoader,
        data_builder: DataLayerBuilder
    ):
        self._odds_client = odds_client
        self._session_factory = session_factory
        self._sports_cache = sports_cache
        self._competitions_cache = competitions_cache
        self._catalog_cache_helper = catalog_cache_helper
        self.policy_loader = policy_loader
        self.data_builder = data_builder

    # TODO: Legacy
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
                            plan_visibility = self._policy_loader.get_visibility_for_category("odds_api", category)
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
            
            # Get API Football mapping from policy
            api_fb = self._policy_loader.get_api_football("odds_api")
            api_fb_by_slug = api_fb.competitions if api_fb else {}
            
            # Create session and upsert competitions
            synced_count = 0
            async with self._session_factory() as session:
                async with session.begin():
                    competitions_repository = CompetitionsRepository(session)
                    
                    for item in resp:
                        try:
                            slug_key = item.get("key", "").strip()
                            title = item.get("title", "")
                            description = item.get("description", "")
                            category = item.get("group", "").lower().strip()
                            # Normalize category: replace spaces with underscores
                            normalized_category = category.replace(" ", "_")
                            is_active = item.get("active", True)
                            
                            if not slug_key or not normalized_category:
                                logger.warning("invalid_competition_data", data=item)
                                continue
                            
                            # Get sport_id for this category (use normalized category)
                            sport_id = category_to_sport_id.get(normalized_category)
                            if not sport_id:
                                logger.warning("sport_not_found_for_category", category=normalized_category)
                                continue
                            
                            # Get plan visibility from policy
                            plan_visibility = self._policy_loader.get_visibility_for_competition("odds_api", slug_key)
                            
                            # Check for API Football mapping
                            api_sources = None
                            api_fb_comp = api_fb_by_slug.get(slug_key)
                            if api_fb_comp:
                                api_sources = {
                                    "api_football": {
                                        "league_id": api_fb_comp.league_id,
                                        "seasons": {
                                            "current": api_fb_comp.seasons.current,
                                            "previous": api_fb_comp.seasons.previous
                                        }
                                    }
                                }

                            # Upsert competition
                            await competitions_repository.get_or_create(
                                sport_id=sport_id,
                                slug_key=slug_key,
                                title=title,
                                description=description if description else None,
                                plan_visibility=plan_visibility,
                                provider="odds_api",
                                api_sources=api_sources
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
                                        slug_key=comp.slug_key,
                                        title=comp.title,
                                        plan_visibility=comp.plan_visibility,
                                        is_active=comp.is_active,
                                        api_sources=comp.api_sources or {},
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

    async def get_competitions_catalog(self, category: str, plan: Literal["free", "pro", "all_available"]) -> List[CompetitionReadDTO]:
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
                CompetitionReadDTO(
                    id=comp.id,
                    sport_id=comp.sport_id,
                    title=comp.title,
                    slug_key=comp.slug_key,
                    plan_visibility=comp.plan_visibility,
                    is_active=comp.is_active,
                    api_sources=comp.api_sources or {},
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

    # TODO: NEW

    async def fetch_and_prepare_sports(self, visibility_sports_map: dict[str, str], visibility_competitions_map: dict[str, str]) -> SportsAndCompetitionsDTO:
        """
        Fetch raw sports data and normalize via builder.

        Fetches sports from provider, wraps into SportList model,
        and normalizes via DataLayerBuilder for both sports and competitions.

        Returns:
            SportsAndCompetitionsDTO with normalized sports and competitions
        """
        logger.debug("fetch_and_prepare_sports_started")

        try:
            # Fetch raw sports data
            raw_sports = await self._odds_client.get_sports()
            logger.info("fetch_and_prepare_sports_received", count=len(raw_sports.sports))

            # Normalize sports via builder
            sports_dto = self.data_builder.normalize_sports(raw_sports, visibility_sports_map)

            # Normalize competitions via builder
            competitions = self.data_builder.normalize_competitions(raw_sports, visibility_competitions_map)

            logger.info(
                "fetch_and_prepare_sports_completed",
                sports_count=len(sports_dto),
                competitions_count=len(competitions),
            )

            return SportsAndCompetitionsDTO(
                sports=sports_dto,
                competitions=competitions,
            )

        except Exception as e:
            logger.error("fetch_and_prepare_sports_failed", error=str(e), exc_info=True)
            return SportsAndCompetitionsDTO(sports=[], competitions=[])

    async def save_sports_and_competitions(self, dto: SportsAndCompetitionsDTO) -> dict[str, int]:
        """
        Save sports and competitions to database and update cache.
        
        Upserts sports first, then maps competitions to sports by category,
        upserts competitions with sport_id injected, and writes to cache.
        
        Args:
            dto: SportsAndCompetitionsDTO containing sports and competitions to save
            
        Returns:
            Dict with sports and competitions counts
        """
        sports_dto = dto.sports
        competitions_entities = dto.competitions
        
        # Early return if both lists are empty
        if not sports_dto and not competitions_entities:
            logger.debug("save_sports_and_competitions_empty_input")
            return {"sports": 0, "competitions": 0}
        
        logger.debug(
            "save_sports_and_competitions_started",
            sports_count=len(sports_dto),
            competitions_count=len(competitions_entities),
        )
        
        try:
            async with self._session_factory() as session:
                sports_repo = SportRepository(session)
                comps_repo = CompetitionsRepository(session)
                
                # Upsert sports first
                logger.info("bulk_upsert_sports_started", count=len(sports_dto))
                saved_sports = await sports_repo.bulk_upsert(sports_dto)
                logger.debug(
                    "bulk_upsert_sports_completed",
                    input_count=len(sports_dto),
                    upserted_count=len(saved_sports),
                )
                
                # Build mapping: category -> sport_id
                saved_map = {model.category: model.id for model in saved_sports}
                # Build reverse mapping: sport_id -> category
                sport_id_to_category = {model.id: model.category for model in saved_sports}
                
                # Inject sport_id into competitions using comp.category
                # Filter out competitions without matching sport
                valid_competitions = []
                for comp in competitions_entities:
                    sport_id = saved_map.get(comp.category)
                    if sport_id:
                        comp.sport_id = sport_id
                        valid_competitions.append(comp)
                    else:
                        logger.warning(
                            "competition_skipped_no_sport",
                            slug_key=comp.slug_key,
                            category=comp.category,
                        )
                
                # Upsert competitions
                logger.info("bulk_upsert_competitions_started", count=len(valid_competitions))
                saved_competitions = await comps_repo.bulk_upsert(valid_competitions) if valid_competitions else []
                logger.debug(
                    "bulk_upsert_competitions_completed",
                    input_count=len(valid_competitions),
                    upserted_count=len(saved_competitions),
                )
                
                # Commit transaction
                await session.commit()
                
                # Write sports cache
                await self._sports_cache.set_catalog({
                    "sports": [
                        {
                            "id": str(s.id),
                            "category": s.category,
                            "is_active": s.is_active,
                            "plan_visibility": s.plan_visibility,
                        }
                        for s in saved_sports
                    ]
                })
                
                # Group competitions by category and write cache
                competitions_by_category: dict[str, list] = {}
                for c in saved_competitions:
                    category = sport_id_to_category.get(c.sport_id)
                    if category:
                        if category not in competitions_by_category:
                            competitions_by_category[category] = []
                        competitions_by_category[category].append(c)
                
                # Write competitions cache by category
                for category, comps in competitions_by_category.items():
                    await self._competitions_cache.set_catalog(
                        category,
                        {
                            "competitions": [
                                {
                                    "id": str(c.id),
                                    "title": c.title,
                                    "sport_id": str(c.sport_id),
                                    "slug_key": c.slug_key,
                                    "plan_visibility": c.plan_visibility,
                                    "api_sources": c.api_sources,
                                    "is_active": c.is_active,
                                }
                                for c in comps
                            ]
                        }
                    )
                
                logger.info(
                    "save_sports_and_competitions_completed",
                    sports_count=len(saved_sports),
                    competitions_count=len(saved_competitions),
                )
                
                return {
                    "sports": len(saved_sports),
                    "competitions": len(saved_competitions),
                }
                
        except Exception as e:
            logger.error(
                "save_sports_and_competitions_failed",
                error=str(e),
                sports_count=len(sports_dto) if sports_dto else 0,
                competitions_count=len(competitions_entities) if competitions_entities else 0,
                exc_info=True,
            )
            raise
