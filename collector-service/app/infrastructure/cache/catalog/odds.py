"""
Odds cache for storing normalized odds_models per event with atomic updates.
"""
from typing import Optional
from uuid import UUID
import structlog
from redis.asyncio import Redis

from app.domain.entities.odds_models.odds import NormalizedOddsDTO, NormalizedOddsCacheDTO
from app.config.settings import settings

logger = structlog.get_logger()


class OddsCache:
    """Cache for normalized odds_models grouped by event_id."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.key_prefix = "catalog:odds_models"

    def _make_key(self, provider_key: str, event_id: UUID) -> str:
        """Generate cache key for an event's normalized odds_models."""
        return f"{self.key_prefix}:{provider_key}:{event_id}"

    def _make_temp_key(self, provider_key: str, event_id: UUID) -> str:
        """Generate temporary key for atomic swap."""
        return f"{self.key_prefix}:{provider_key}:{event_id}:tmp"

    async def write_event_odds_atomic(
        self,
        provider_key: str,
        event_id: UUID,
        items: list[NormalizedOddsDTO],
        ttl_sec: Optional[int] = None
    ) -> None:
        """
        Atomically write normalized odds_models for an event.

        Uses atomic swap pattern:
        1. Write to temporary key
        2. Rename temporary key to final key
        3. Set TTL if provided (defaults to cache_ttl_odds_sec from settings)

        If items is empty, deletes the key.

        Args:
            provider_key: Competition provider_key
            event_id: Event UUID
            items: List of NormalizedOddsDTO objects
            ttl_sec: Optional TTL in seconds (defaults to settings.cache_ttl_odds_sec)
        """
        if ttl_sec is None:
            ttl_sec = settings.cache_ttl_odds_sec
        final_key = self._make_key(provider_key, event_id)

        if not items:
            try:
                await self.redis.delete(final_key)
                logger.info(
                    "odds_cache_event_cleared_empty",
                    provider_key=provider_key,
                    event_id=str(event_id)
                )
            except Exception as e:
                logger.error(
                    "failed_to_clear_odds_cache",
                    provider_key=provider_key,
                    event_id=str(event_id),
                    error=str(e)
                )
            return

        temp_key = self._make_temp_key(provider_key, event_id)

        try:
            pipe = self.redis.pipeline()
            await pipe.delete(temp_key)

            for item in items:
                # Map NormalizedOddsDTO to NormalizedOddsCacheDTO (exclude id and created_at)
                cache_item = NormalizedOddsCacheDTO(
                    event_id=item.event_id,
                    market_type=item.market_type,
                    home_odds_avg=item.home_odds_avg,
                    away_odds_avg=item.away_odds_avg,
                    draw_odds_avg=item.draw_odds_avg,
                    home_odds_best=item.home_odds_best,
                    away_odds_best=item.away_odds_best,
                    draw_odds_best=item.draw_odds_best,
                    bookmakers_count=item.bookmakers_count,
                    timestamp_source=item.timestamp_source,
                    timestamp_ingested=item.timestamp_ingested,
                    timestamp_normalized=item.timestamp_normalized,
                )
                item_data = cache_item.model_dump_json()
                await pipe.rpush(temp_key, item_data)

            await pipe.execute()

            await self.redis.rename(temp_key, final_key)

            if ttl_sec:
                await self.redis.expire(final_key, ttl_sec)

            logger.info(
                "odds_cache_event_updated_atomic",
                provider_key=provider_key,
                event_id=str(event_id),
                count=len(items),
                ttl_sec=ttl_sec
            )

        except Exception as e:
            logger.error(
                "odds_cache_update_failed",
                provider_key=provider_key,
                event_id=str(event_id),
                error=str(e),
                exc_info=True
            )
            try:
                await self.redis.delete(temp_key)
            except Exception:
                pass

    async def read_event_odds(
        self,
        provider_key: str,
        event_id: UUID
    ) -> list[NormalizedOddsDTO]:
        """
        Read normalized odds_models for an event from cache.

        Args:
            provider_key: Competition provider_key
            event_id: Event UUID

        Returns:
            List of NormalizedOddsDTO objects (empty if not found)
        """
        final_key = self._make_key(provider_key, event_id)

        try:
            raw_items = await self.redis.lrange(final_key, 0, -1)

            items = []
            for raw_item in raw_items:
                try:
                    # Deserialize from cache DTO to full DTO
                    cache_item = NormalizedOddsCacheDTO.model_validate_json(raw_item)
                    item = NormalizedOddsDTO(
                        id=None,
                        event_id=cache_item.event_id,
                        market_type=cache_item.market_type,
                        home_odds_avg=cache_item.home_odds_avg,
                        away_odds_avg=cache_item.away_odds_avg,
                        draw_odds_avg=cache_item.draw_odds_avg,
                        home_odds_best=cache_item.home_odds_best,
                        away_odds_best=cache_item.away_odds_best,
                        draw_odds_best=cache_item.draw_odds_best,
                        bookmakers_count=cache_item.bookmakers_count,
                        timestamp_source=cache_item.timestamp_source,
                        timestamp_ingested=cache_item.timestamp_ingested,
                        timestamp_normalized=cache_item.timestamp_normalized,
                        created_at=None,
                    )
                    items.append(item)
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_cached_odds",
                        provider_key=provider_key,
                        event_id=str(event_id),
                        error=str(e)
                    )

            logger.debug(
                "odds_cache_retrieved",
                provider_key=provider_key,
                event_id=str(event_id),
                count=len(items)
            )
            return items

        except Exception as e:
            logger.error(
                "odds_cache_retrieval_failed",
                provider_key=provider_key,
                event_id=str(event_id),
                error=str(e)
            )
            return []

