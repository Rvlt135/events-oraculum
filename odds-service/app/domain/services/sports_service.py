"""
Sports service for managing sports data synchronization.
"""
from typing import List, Dict, Any
import structlog
from prometheus_client import Counter, Histogram

from app.domain.ports.sports_provider import SportsProvider
from app.domain.ports.sports_repository import SportsRepository
from app.infra.unit_of_work import UnitOfWork

logger = structlog.get_logger()

# Metrics
sports_sync_duration = Histogram("sports_sync_duration_seconds", "Time spent syncing sports data")
sports_synced_total = Counter("sports_synced_total", "Total number of sports synced")
sports_sync_errors_total = Counter("sports_sync_errors_total", "Total number of sports sync errors")


class SportsService:
    """Service for managing sports data synchronization."""

    def __init__(
        self,
        sports_provider: SportsProvider,
        sports_repository: SportsRepository,
        unit_of_work: UnitOfWork,
    ):
        self.sports_provider = sports_provider
        self.sports_repository = sports_repository
        self.unit_of_work = unit_of_work

    async def sync_from_odds(self) -> Dict[str, Any]:
        """
        Sync sports data from external provider.
        
        Uses UoW pattern with one commit per batch.
        Implements idempotent upsert by sport key.
        Updates Redis cache on success.
        
        Returns:
            Sync result with counts and status
        """
        logger.info("sports_sync_started")
        
        try:
            # Fetch sports data from external provider
            sports_data = await self.sports_provider.get_sports()
            logger.info("sports_data_fetched", count=len(sports_data))
            
            synced_count = 0
            
            # Use UoW for batch processing
            async with self.unit_of_work:
                for sport_data in sports_data:
                    try:
                        # Extract sport key and name
                        sport_key = sport_data.get("key", "").lower()
                        sport_name = sport_data.get("title", sport_key.title())
                        
                        if not sport_key:
                            logger.warning("invalid_sport_data", data=sport_data)
                            continue
                        
                        # Idempotent upsert by sport key
                        sport_id = await self.sports_repository.upsert(sport_key, sport_name)
                        
                        logger.debug(
                            "sport_upserted",
                            key=sport_key,
                            name=sport_name,
                            sport_id=str(sport_id)
                        )
                        synced_count += 1
                        
                    except Exception as e:
                        logger.error(
                            "sport_upsert_failed",
                            sport_data=sport_data,
                            error=str(e)
                        )
                        sports_sync_errors_total.inc()
                
                # Commit all changes in one transaction
                await self.unit_of_work.commit()
                logger.info("sports_batch_committed", count=synced_count)
            
            # Update Redis cache on success
            await self._update_redis_cache()
            
            sports_synced_total.inc(synced_count)
            
            result = {
                "status": "success",
                "synced_count": synced_count,
                "total_fetched": len(sports_data),
            }
            
            logger.info("sports_sync_completed", **result)
            return result
            
        except Exception as e:
            logger.error("sports_sync_failed", error=str(e))
            sports_sync_errors_total.inc()
            return {
                "status": "error",
                "message": str(e),
                "synced_count": 0,
            }

    async def _update_redis_cache(self) -> None:
        """Update Redis cache with sports catalog."""
        try:
            # Get all sports for cache
            sports = await self.sports_repository.get_all()
            
            # Update Redis key with TTL
            cache_data = {
                "sports": [
                    {
                        "id": str(sport.id),
                        "key": sport.name,  # Using name as key
                        "name": sport.display_name,
                    }
                    for sport in sports
                ],
                "updated_at": str(sports[0].created_at) if sports else None,
            }
            
            # Set cache with TTL (5-15 minutes)
            if self.unit_of_work.redis:
                import json
                await self.unit_of_work.redis.setex(
                    "catalog:sports",
                    600,  # 10 minutes TTL
                    json.dumps(cache_data)
                )
            
            logger.info("sports_cache_updated", count=len(sports))
            
        except Exception as e:
            logger.error("sports_cache_update_failed", error=str(e))
            # Don't fail the main operation if cache update fails
