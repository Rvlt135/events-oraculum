"""
Sports service for managing sports data synchronization.
"""
from typing import Dict, Any, List
import structlog
from prometheus_client import Counter, Histogram
import json
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid import UUID

from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.infrastructure.repositories.sport import SportRepository
from app.infrastructure.cache.sports import SportsCache
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
    ):
        self._odds_client = odds_client
        self._session_factory = session_factory
        self._cache = sports_cache


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
            
            # Extract unique categories (groups)
            unique_categories = set()
            for item in resp:
                group = item.get("group", "").lower().strip()
                if group:
                    unique_categories.add(group)
            
            logger.info("unique_categories_extracted", count=len(unique_categories))
            
            # Create session and upsert categories
            synced_count = 0
            async with self._session_factory() as session:
                async with session.begin():
                    sport_repository = SportRepository(session)
                    
                    for category in sorted(unique_categories):
                        try:
                            await sport_repository.get_or_create(category)
                            synced_count += 1
                            logger.debug("sport_category_upserted", category=category)
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
            
            # Create session and upsert competitions
            synced_count = 0
            async with self._session_factory() as session:
                # Create mapping of category -> sport_id within the same session
                category_to_sport_id = await self._get_category_to_sport_id_mapping(session)
                
                async with session.begin():
                    competitions_repository = CompetitionsRepository(session)
                    
                    for item in resp:
                        try:
                            provider_key = item.get("key", "").strip()
                            title = item.get("title", "")
                            description = item.get("description", "")
                            category = item.get("group", "").lower().strip()
                            is_active = item.get("active", True)
                            
                            if not provider_key or not category:
                                logger.warning("invalid_competition_data", data=item)
                                continue
                            
                            # Get sport_id for this category
                            sport_id = category_to_sport_id.get(category)
                            if not sport_id:
                                logger.warning("sport_not_found_for_category", category=category)
                                continue
                            
                            # Upsert competition
                            await competitions_repository.get_or_create(
                                sport_id=sport_id,
                                provider_key=provider_key,
                                title=title,
                                description=description if description else None
                            )
                            
                            synced_count += 1
                            logger.debug("competition_upserted", key=provider_key, title=title)
                            
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
                await self._update_categories_sport_redis_cache()
            
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
    
    async def _update_categories_sport_redis_cache(self) -> None:
        """Update Redis cache with sports catalog."""
        try:
            # Get all sports for cache using a fresh session
            async with self._session_factory() as session:
                sport_repository = SportRepository(session)
                sports = await sport_repository.get_all()
                
                # Update Redis key with TTL
                cache_data = {
                    "sports": [
                        {
                            "id": str(sport.id),
                            "category": sport.category,
                            "is_active": sport.is_active,
                        }
                        for sport in sports
                    ],
                    "updated_at": str(sports[0].created_at) if sports else None,
                }
                
                # Set cache with TTL
                if self._cache:
                    await self._cache.set_catalog(cache_data)
                
                logger.info("sports_cache_updated", count=len(sports))
            
        except Exception as e:
            logger.error("sports_cache_update_failed", error=str(e))
            # Don't fail the main operation if cache update fails
