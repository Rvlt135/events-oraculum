from typing import List

from redis.asyncio import Redis
from app.config.settings import settings
import structlog

from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO

CATALOG_TTL_SEC = settings.cache_ttl_features_sec
KEY_PREFIX = "features"

class TeamFeaturesCache:
    """Redis cache layer for team features"""

    def __init__(self, redis: Redis) -> None:
        self._r = redis


    async def save_team_features(self, features: List[TeamFeaturesDTO]) -> TeamFeaturesDTO:
        NotImplemented()