import json
from typing import List, Optional
from uuid import UUID

from redis.asyncio import Redis
from app.config.settings import settings
import structlog

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.models_layer.elo_model import EloModelDTO

CATALOG_TTL_SEC = settings.cache_ttl_features_sec
KEY_PREFIX = "features"

logger = structlog.get_logger()

def _key_features_team(team_id: UUID, competition_id: UUID, season: int) -> str:
    """Generate Redis key for team features."""
    return f"{KEY_PREFIX}:team:{team_id}:{competition_id}:{season}"

def _key_feature_matcher_team(team_id: UUID, competition_id: UUID, season: int) -> str:
    """Generate Redis key for team features."""
    return f"{KEY_PREFIX}:match:{team_id}:{competition_id}:{season}"

def _key_poisson_features(event_id: UUID) -> str:
    """Generate Redis key for poisson features."""
    return f"poisson:event:{event_id}"

class TeamFeaturesCache:
    """Redis cache layer for team features"""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    def _deserialize_team_features(self, raw_value: Optional[str]) -> Optional[TeamFeaturesDTO]:
        """Deserialize raw JSON string to TeamFeaturesDTO.
        
        Args:
            raw_value: Raw JSON string from cache or None.
            
        Returns:
            TeamFeaturesDTO if valid, None otherwise.
        """
        if not raw_value:
            return None
        
        try:
            data = json.loads(raw_value)
            return TeamFeaturesDTO(**data)
        except Exception:
            return None

    def _deserialize_match_features(self, raw_value: Optional[str]) -> Optional[MatchFeaturesDTO]:
        """Deserialize raw JSON string to MatchFeaturesDTO.
        
        Args:
            raw_value: Raw JSON string from cache or None.
            
        Returns:
            MatchFeaturesDTO if valid, None otherwise.
        """
        if not raw_value:
            return None
        
        try:
            data = json.loads(raw_value)
            return MatchFeaturesDTO(**data)
        except Exception:
            return None

    def _deserialize_poisson_features(self, raw_value: Optional[str]) -> Optional[PoissonFeaturesDTO]:
        """Deserialize raw JSON string to PoissonFeaturesDTO.

        Args:
            raw_value: Raw JSON string from cache or None.

        Returns:
            PoissonFeaturesDTO if valid, None otherwise.
        """
        if not raw_value:
            return None

        try:
            data = json.loads(raw_value)
            return PoissonFeaturesDTO(**data)
        except Exception:
            return None

    async def save_team_features(self, features: List[TeamFeaturesDTO]) -> None:
        """Store team features in Redis."""
        async with self._r.pipeline() as pipe:
            for feature in features:
                key = _key_features_team(feature.team_id, feature.competition_id, feature.season)
                data = feature.model_dump(mode="json")
                json_str = json.dumps(data, ensure_ascii=False)
                await self._r.set(key, json_str)
            await pipe.execute()

    async def save_match_features(self, features: List[MatchFeaturesDTO]):
        """Store match features in Redis."""
        async with self._r.pipeline() as pipe:
            for feature in features:
                key = _key_feature_matcher_team(feature.team_id, feature.competition_id, feature.season)
                data = feature.model_dump(mode="json")
                json_str = json.dumps(data, ensure_ascii=False)
                await self._r.set(key, json_str)
            await pipe.execute()
            logger.info(f"Saving match features in Redis count: {len(features)}")

    async def save_poisson_features(self, features: list[PoissonFeaturesDTO]):
        """Store poisson features in Redis."""
        logger.debug("cache_save_poisson_features_called", items_count=len(features))
        if features:
            logger.debug("cache_save_poisson_features_first_event", event_id=str(features[0].event_id))
        async with self._r.pipeline() as pipe:
            for feature in features:
                key = _key_poisson_features(feature.event_id)
                data = feature.model_dump(mode="json")
                json_str = json.dumps(data, ensure_ascii=False)
                await pipe.set(key, json_str)
            await pipe.execute()
        logger.debug("cache_save_poisson_features_completed", items_count=len(features))

    async def get_team_features_by_team_ids(
        self,
        team_ids: list[UUID],
        competition_id: UUID,
        season: int,
    ) -> dict[UUID, TeamFeaturesDTO]:
        """Get team features from cache by team IDs.
        
        Args:
            team_ids: List of team identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Dictionary mapping team_id to TeamFeaturesDTO (cache hits only).
        """
        if not team_ids:
            return {}
        
        # keys = [
        #     _key_features_team(team_id, competition_id, season)
        #     for team_id in team_ids
        # ]
        
        async with self._r.pipeline() as pipe:
            for team_id in team_ids:
                key = _key_features_team(team_id, competition_id, season)
            # for key in keys:
                await pipe.get(key)
            raw_values = await pipe.execute()
        
        result = {}
        for team_id, raw_value in zip(team_ids, raw_values):
            dto = self._deserialize_team_features(raw_value)
            if dto is not None:
                result[team_id] = dto
        
        logger.debug("team_features_cache_completed", total=len(result))
        return result


    async def get_match_features_by_team_ids(
        self,
        team_ids: list[UUID],
        competition_id: UUID,
        season: int,
    ) -> dict[UUID, MatchFeaturesDTO]:
        """Get match features from cache by team IDs.
        
        Args:
            team_ids: List of team identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Dictionary mapping team_id to MatchFeaturesDTO (cache hits only).
        """
        if not team_ids:
            return {}
        
        # keys = [
        #     _key_feature_matcher_team(team_id, competition_id, season)
        #     for team_id in team_ids
        # ]

        async with self._r.pipeline() as pipe:
            for team_id in team_ids:
                key = _key_feature_matcher_team(team_id, competition_id, season)
                # for key in keys:
                await pipe.get(key)
            raw_values = await pipe.execute()
        
        result = {}
        for team_id, raw_value in zip(team_ids, raw_values):
            dto = self._deserialize_match_features(raw_value)
            if dto is not None:
                result[team_id] = dto
        
        logger.debug("match_features_cache_completed", total=len(result))
        return result

    async def get_poisson_features_by_event_id(
        self,
        event_ids: list[UUID],
    ) -> dict[UUID, PoissonFeaturesDTO]:
        """Get poisson features from cache by event IDs.
        
        Args:
            event_ids: List of event identifiers.
            
        Returns:
            Dictionary mapping event_id to PoissonFeaturesDTO (cache hits only).
        """
        if not event_ids:
            return {}
        
        # keys = [
        #     _key_poisson_features(event_id)
        #     for event_id in event_ids
        # ]
        
        async with self._r.pipeline() as pipe:
            for event_id in event_ids:
                key = _key_poisson_features(event_id)
            # for key in keys:
                await pipe.get(key)
            raw_values = await pipe.execute()
        
        result = {}
        for event_id, raw_value in zip(event_ids, raw_values):
            dto = self._deserialize_poisson_features(raw_value)
            if dto is not None:
                result[event_id] = dto
        
        logger.debug("poisson_features_cache_completed", total=len(result))
        return result
