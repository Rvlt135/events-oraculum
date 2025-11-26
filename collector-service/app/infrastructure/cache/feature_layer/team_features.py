import json
from typing import List
from uuid import UUID

from redis.asyncio import Redis
from app.config.settings import settings
import structlog

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO

CATALOG_TTL_SEC = settings.cache_ttl_features_sec
KEY_PREFIX = "features"

logger = structlog.get_logger()

def _key_features_team(team_id: UUID, competition_id: UUID, season: int) -> str:
    """Generate Redis key for team features."""
    return f"{KEY_PREFIX}:team:{team_id}:{competition_id}:{season}"

def _key_feature_matcher_team(team_id: UUID, competition_id: UUID, season: int) -> str:
    """Generate Redis key for team features."""
    return f"{KEY_PREFIX}:match:{team_id}:{competition_id}:{season}"

class TeamFeaturesCache:
    """Redis cache layer for team features"""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

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
                logger.info(f"Saving match features for team {feature.team_id} in competition {feature.competition_id} in season {feature.season}")
                key = _key_feature_matcher_team(feature.team_id, feature.competition_id, feature.season)
                data = feature.model_dump(mode="json")
                json_str = json.dumps(data, ensure_ascii=False)
                await self._r.set(key, json_str)
            await pipe.execute()
            logger.info(f"Saving match features in Redis count: {len(features)}")
