"""
Service for building team features
"""
from typing import List
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.builders.event_layer.event_layer_builder import EventLayerBuilder
from app.builders.feature_layer.match_features import MatchFeaturesBuilder
from app.builders.feature_layer.poisson_feature_builder import PoissonFeaturesBuilder
from app.builders.feature_layer.team_features import TeamFeaturesBuilder
from app.domain.entities.event_layer.dto import EventFeatureBundleDTO
from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import LastFixtureDTO, UpcomingFixtureDTO
from app.domain.entities.statistics.dto.standings_dto import StandingMinimalDTO
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.events_layer.events_layer_cache import EventsLayerCache
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.infrastructure.repositories.feature_layer.match_features import MatchFeaturesRepository
from app.infrastructure.repositories.feature_layer.poisson_feature import PoissonFeatureRepository
from app.infrastructure.repositories.feature_layer.team_features import TeamFeaturesRepository
from app.infrastructure.repositories.event_layer.event_layer_repo import EventLayerRepository

logger = structlog.get_logger()


class EventLayerService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        team_features_cache: TeamFeaturesCache,
        catalog_cache_helper: CatalogCacheHelper,
        event_layer_builder: EventLayerBuilder,
        event_layer_cache: EventsLayerCache,
    ):
        self.session_factory = session_factory
        self.catalog_cache_helper = catalog_cache_helper
        self.team_features_cache = team_features_cache
        self.el_builder = event_layer_builder
        self.event_layer_cache = event_layer_cache

    async def persist_enriched_events(
        self,
        bundles: list[EventFeatureBundleDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Persist enriched event feature bundles to database and cache.
        
        Args:
            bundles: List of event feature bundle DTOs to persist.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of processed bundles.
        """
        logger.debug(
            "persist_enriched_events_called",
            count=len(bundles),
            competition_id=str(competition_id),
            season=season,
        )
        
        if not bundles:
            return 0
        
        # Build mapping for cache
        items_map: dict[UUID, EventFeatureBundleDTO] = {
            b.event_id: b for b in bundles
        }
        
        # Persist to DB in batch
        async with self.session_factory() as session:
            event_layer_repo = EventLayerRepository(session)
            await event_layer_repo.store_bundles(
                bundles=bundles,
                competition_id=competition_id,
                season=season,
            )
        
        # Persist to cache in batch
        await self.event_layer_cache.set_bundles(
            items=items_map,
            ttl_sec=None,
        )
        
        logger.debug("persist_enriched_events_completed", count=len(bundles))
        
        return len(bundles)