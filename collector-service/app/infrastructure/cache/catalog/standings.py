from typing import Any, Dict, Optional
import json
from uuid import UUID

from redis.asyncio import Redis
from app.config.settings import settings
import structlog

CATALOG_TTL_SEC = settings.cache_ttl_competitions_sec
KEY_PREFIX = "standings"
KEY_PREFIX_FIXTURES = "fixtures_history"


def _key_standings_teams(competition_slug_key: str, season: int) -> str:
    """Generate Redis key for competitions catalog teams by slug_key."""
    teams_key = "{competition_slug_key}:{season}:teams"
    return f"{KEY_PREFIX}:{teams_key.format(competition_slug_key=competition_slug_key, season=season)}"

def _key_fixtures_teams(competition_slug_key: str, season: int) -> str:
    """Generate Redis key for competitions catalog teams by slug_key."""
    teams_key = "{competition_slug_key}:{season}:teams"
    return f"{KEY_PREFIX_FIXTURES}:{teams_key.format(competition_slug_key=competition_slug_key, season=season)}"

class StandingsFootballCache:
    """Redis cache layer for standings football"""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def save_standings_teams(self, competition_slug_key: str, season: int, items: list[dict], ttl: int = CATALOG_TTL_SEC) -> None:
        """Store competitions catalog for a specific category."""
        json_str = json.dumps(items, ensure_ascii=False)
        await self._r.setex(_key_standings_teams(competition_slug_key, season), ttl, json_str)

    async def save_fixtures_items(self, competition_slug_key: str, season: int, items: list[dict], ttl: int = CATALOG_TTL_SEC) -> None:
        """Store fixtures catalog for a specific category."""
        json_str = json.dumps(items, ensure_ascii=False)
        await self._r.setex(_key_fixtures_teams(competition_slug_key, season), ttl, json_str)