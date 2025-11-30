"""
Service for building models layer
"""
from typing import List
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.builders.models_layer.elo_model_builder import EloModelBuilder
from app.builders.models_layer.poisson_model_builder import PoissonModelBuilder
from app.domain.entities.models_layer.dto import ModelScopesDTO
from app.domain.entities.models_layer.elo_model import EloInputFeaturesDTO, EloModelDTO
from app.domain.entities.models_layer.poisson_model import PoissonInputFeaturesDTO, PoissonModelDTO
from app.domain.entities.statistics.dto.fixtures_dto import UpcomingFixtureDTO
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.infrastructure.repositories.feature_layer.match_features import MatchFeaturesRepository
from app.infrastructure.repositories.feature_layer.poisson_feature import PoissonFeatureRepository
from app.infrastructure.repositories.feature_layer.team_features import TeamFeaturesRepository
from app.infrastructure.repositories.models_layer.elo import EloRepository
from app.infrastructure.repositories.models_layer.poisson_repo import PoissonModelRepository
from app.infrastructure.cache.models_layer.models_layer_cache import ModelsLayerCache

logger = structlog.get_logger()


class LayerModelService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        team_features_cache: TeamFeaturesCache,
        catalog_cache_helper: CatalogCacheHelper,
        elo_model_builder: EloModelBuilder,
        poisson_model_builder: PoissonModelBuilder,
        models_layer_cache: ModelsLayerCache
    ):
        self.session_factory = session_factory
        self.catalog_cache_helper = catalog_cache_helper
        self.team_features_cache = team_features_cache
        self.elo_model_builder = elo_model_builder
        self.poisson_model_builder = poisson_model_builder
        self.models_layer_cache = models_layer_cache


    async def extract_features_for_elo_build(
        self,
        events: list[UpcomingFixtureDTO],
        team_ids_set: set[UUID],
        competition_id: UUID,
        season: int,
    ) -> EloInputFeaturesDTO:
        """Extract features for Elo model building.
        
        Args:
            events: List of upcoming fixtures.
            team_ids_set: Set of team identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            EloInputFeaturesDTO with all required features.
        """
        team_ids = list(team_ids_set)
        event_ids = [e.event_id for e in events]
        
        async with self.session_factory() as session:
            # TEAM FEATURES (cache → repo fallback)
            cached_tf = await self.team_features_cache.get_team_features_by_team_ids(
                team_ids=team_ids,
                competition_id=competition_id,
                season=season,
            )
            missing_tf_ids = team_ids_set - cached_tf.keys()
            repo_tf = {}
            if missing_tf_ids:
                repo_tf = await TeamFeaturesRepository(session).get_by_team_ids(
                    team_ids=missing_tf_ids,
                    competition_id=competition_id,
                    season=season,
                )
                # save to cache
                await self.team_features_cache.save_team_features(list(repo_tf.values()))
            team_features = {**cached_tf, **repo_tf}
            
            # MATCH FEATURES (cache → repo fallback)
            cached_mf = await self.team_features_cache.get_match_features_by_team_ids(
                team_ids=team_ids,
                competition_id=competition_id,
                season=season,
            )
            missing_mf_ids = team_ids_set - cached_mf.keys()
            repo_mf = {}
            if missing_mf_ids:
                repo_mf = await MatchFeaturesRepository(session).get_by_team_ids(
                    team_ids=missing_mf_ids,
                    competition_id=competition_id,
                    season=season,
                )
                await self.team_features_cache.save_match_features(list(repo_mf.values()))
            match_features = {**cached_mf, **repo_mf}
            
            # POISSON FEATURES (cache → repo fallback)
            cached_pf = await self.team_features_cache.get_poisson_features_by_event_id(event_ids)
            missing_pf_ids = set(event_ids) - cached_pf.keys()
            repo_pf = {}
            if missing_pf_ids:
                repo_pf = await PoissonFeatureRepository(session).get_by_event_ids(
                    event_ids=missing_pf_ids
                )
                await self.team_features_cache.save_poisson_features(list(repo_pf.values()))
            poisson_features = {**cached_pf, **repo_pf}
        
        logger.debug(
            "elo_features_extracted",
            events=len(events),
            team_features=len(team_features),
            match_features=len(match_features),
            poisson_features=len(poisson_features),
        )
        
        return EloInputFeaturesDTO(
            events=events,
            team_features=team_features,
            match_features=match_features,
            poisson_features=poisson_features,
        )

    async def save_elo_model(
        self,
        elo_model: list[EloModelDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Save Elo model predictions to database and cache.
        
        Args:
            elo_model: List of EloModelDTO records.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of records saved to database.
        """
        if not elo_model:
            return 0
        
        async with self.session_factory() as session:
            repo_count = await EloRepository(session).bulk_upsert_elo_model(elo_model, competition_id, season)
        
        cache_count = await self.models_layer_cache.save_elo_events(
            elo_outputs=elo_model,
            competition_id=competition_id,
            season=season,
        )
        
        logger.debug("elo_model_saved", db=repo_count, cache=cache_count)
        return repo_count

    async def extract_features_for_poisson_build(
            self,
            events: list[UpcomingFixtureDTO],
            team_ids_set: set[UUID],
            competition_id: UUID,
            season: int,
    ) -> PoissonInputFeaturesDTO:
        """Extract features for Poisson model building.

        Args:
            events: List of upcoming fixtures.
            team_ids_set: Set of team identifiers.
            competition_id: Competition identifier.
            season: Season year.

        Returns:
            PoissonInputFeaturesDTO with all required features.
        """
        team_ids = list(team_ids_set)
        event_ids = [e.event_id for e in events]

        async with self.session_factory() as session:
            # TEAM FEATURES (cache → repo fallback)
            cached_tf = await self.team_features_cache.get_team_features_by_team_ids(
                team_ids=team_ids,
                competition_id=competition_id,
                season=season,
            )
            missing_tf_ids = team_ids_set - cached_tf.keys()
            repo_tf = {}
            if missing_tf_ids:
                repo_tf = await TeamFeaturesRepository(session).get_by_team_ids(
                    team_ids=missing_tf_ids,
                    competition_id=competition_id,
                    season=season,
                )
                # save to cache
                await self.team_features_cache.save_team_features(list(repo_tf.values()))
            team_features = {**cached_tf, **repo_tf}

            # MATCH FEATURES (cache → repo fallback)
            cached_mf = await self.team_features_cache.get_match_features_by_team_ids(
                team_ids=team_ids,
                competition_id=competition_id,
                season=season,
            )
            missing_mf_ids = team_ids_set - cached_mf.keys()
            repo_mf = {}
            if missing_mf_ids:
                repo_mf = await MatchFeaturesRepository(session).get_by_team_ids(
                    team_ids=missing_mf_ids,
                    competition_id=competition_id,
                    season=season,
                )
                await self.team_features_cache.save_match_features(list(repo_mf.values()))
            match_features = {**cached_mf, **repo_mf}

            # POISSON FEATURES (cache → repo fallback)
            cached_pf = await self.team_features_cache.get_poisson_features_by_event_id(event_ids)
            missing_pf_ids = set(event_ids) - cached_pf.keys()
            repo_pf = {}
            if missing_pf_ids:
                repo_pf = await PoissonFeatureRepository(session).get_by_event_ids(
                    event_ids=missing_pf_ids
                )
                await self.team_features_cache.save_poisson_features(list(repo_pf.values()))
            poisson_features = {**cached_pf, **repo_pf}

        logger.debug(
            "poisson_features_extracted",
            events=len(events),
            team_features=len(team_features),
            match_features=len(match_features),
            poisson_features=len(poisson_features),
        )

        return PoissonInputFeaturesDTO(
            events=events,
            team_features=team_features,
            match_features=match_features,
            poisson_features=poisson_features,
        )

    async def save_poisson_model(
        self,
        outputs: list[PoissonModelDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Save Poisson model predictions to database and cache.
        
        Args:
            outputs: List of PoissonModelDTO records.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of records saved to database.
        """
        logger.debug("poisson_model_save_started", count=len(outputs))
        
        if not outputs:
            return 0
        
        async with self.session_factory() as session:
            repo = PoissonModelRepository(session)
            count_db = await repo.bulk_upsert_poisson_model(
                outputs=outputs,
                competition_id=competition_id,
                season=season,
            )
        
        logger.debug("poisson_model_db_saved", count=count_db)
        
        try:
            count_cache = await self.models_layer_cache.save_poisson_events(
                outputs=outputs,
                competition_id=competition_id,
                season=season,
            )
            logger.debug("poisson_model_cache_saved", count=count_cache)
        except Exception as e:
            logger.debug("poisson_model_cache_error", error=str(e))
        
        return count_db

    async def extract_model_scopes(
        self,
        events: list[UpcomingFixtureDTO],
        competition_id: UUID,
        season: int,
    ) -> ModelScopesDTO:
        """Extract model scopes (Elo and Poisson outputs) for events.
        
        Args:
            events: List of upcoming fixtures.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            ModelScopesDTO with Elo and Poisson model outputs.
        """
        logger.debug("extract_model_scopes_started", events_count=len(events))
        
        event_ids = [f.event_id for f in events]
        
        if not event_ids:
            return ModelScopesDTO(
                elo_outputs={},
                poisson_outputs={},
            )
        
        event_ids_set = set(event_ids)
        
        # Read Elo from cache
        elo_cached = await self.models_layer_cache.get_elo_by_event_ids(
            event_ids=event_ids,
            competition_id=competition_id,
            season=season,
        )
        missing_elo = event_ids_set - elo_cached.keys()
        
        # Read Poisson from cache
        poisson_cached = await self.models_layer_cache.get_poisson_by_event_ids(
            event_ids=event_ids,
            competition_id=competition_id,
            season=season,
        )
        missing_poisson = event_ids_set - poisson_cached.keys()
        
        # Open ONE session for all repo calls
        elo_repo = {}
        poisson_repo = {}
        if missing_elo or missing_poisson:
            async with self.session_factory() as session:
                if missing_elo:
                    elo_repo = await EloRepository(session).get_by_event_ids(
                        event_ids=list(missing_elo),
                        competition_id=competition_id,
                        season=season,
                    )
                if missing_poisson:
                    poisson_repo = await PoissonModelRepository(session).get_by_event_ids(
                        event_ids=list(missing_poisson),
                        competition_id=competition_id,
                        season=season,
                    )
        
        # Merge cached + repo results
        elo_outputs = {**elo_cached, **elo_repo}
        poisson_outputs = {**poisson_cached, **poisson_repo}
        
        logger.debug(
            "extract_model_scopes_completed",
            elo_count=len(elo_outputs),
            poisson_count=len(poisson_outputs),
        )
        
        return ModelScopesDTO(
            elo_outputs=elo_outputs,
            poisson_outputs=poisson_outputs,
        )