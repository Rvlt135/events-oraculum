import json
from typing import List
from uuid import UUID

from redis.asyncio import Redis
from app.config.settings import settings
import structlog

from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO

CATALOG_TTL_SEC = settings.cache_ttl_features_sec
KEY_PREFIX = "features"


def _key_features_team(team_id: UUID, competition_id: UUID, season: int) -> str:
    """Generate Redis key for team features."""
    return f"{KEY_PREFIX}:team:{team_id}:{competition_id}:{season}"

class TeamFeaturesCache:
    """Redis cache layer for team features"""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def save_team_features(self, features: List[TeamFeaturesDTO]) -> None:
        """Store team features in Redis."""
        for feature in features:
            key = _key_features_team(feature.team_id, feature.competition_id, feature.season)
            data = feature.model_dump()
            json_str = json.dumps(data, ensure_ascii=False)
            await self._r.set(key, json_str)