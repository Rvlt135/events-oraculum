from __future__ import annotations
from typing import Any, Dict, Optional
import json
from uuid import UUID

from redis.asyncio import Redis
from app.config.settings import settings
import structlog

CATALOG_TTL_SEC = settings.cache_ttl_competitions_sec
KEY_PREFIX = "catalog:competitions"


def _normalize_category(category: str) -> str:
    """Normalize category name by replacing spaces with underscores."""
    return category.replace(" ", "_")


def _key_catalog(category: str) -> str:
    """Generate Redis key for competitions catalog by category."""
    normalized = _normalize_category(category)
    return f"{KEY_PREFIX}:{normalized}"

def _key_catalog_teams(slug_key: str, season: int) -> str:
    """Generate Redis key for competitions catalog teams by slug_key."""
    teams_key = "{slug_key}:{season}:teams"
    return f"{KEY_PREFIX}:{teams_key.format(slug_key=slug_key, season=season)}"

class CompetitionsCache:
    """Redis cache layer for competitions catalog."""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def set_catalog(self, category: str, items: Dict, ttl: int = CATALOG_TTL_SEC) -> None:
        """Store competitions catalog for a specific category."""
        json_str = json.dumps(items, ensure_ascii=False)
        await self._r.setex(_key_catalog(category), ttl, json_str)

    async def get_catalog(self, category: str) -> Optional[Dict[str, Any]]:
        """Retrieve competitions catalog for a specific category."""
        raw = await self._r.get(_key_catalog(category))
        if not raw:
            return None
        try:
            # Handle both string and bytes responses
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            # Log error and invalidate corrupted cache
            logger = structlog.get_logger()
            logger.warning("cache_decode_error", error=str(e), raw_type=type(raw).__name__, category=category)
            await self.invalidate_catalog(category)
            return None

    async def set_competition_team_slugs(self, competition_slug_key: str, season: int, team_slugs: list[str], ttl: int = CATALOG_TTL_SEC) -> None:
        json_str = json.dumps(team_slugs, ensure_ascii=False)
        await self._r.setex(_key_catalog_teams(competition_slug_key, season), ttl, json_str)

    async def get_competition_team_slugs(self, competition_slug_key: str, season: int) -> list[str] | None:
        raw = await self._r.get(_key_catalog_teams(competition_slug_key, season))
        if not raw:
            return None
        try:
            # Handle both string and bytes responses
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            # Log error and invalidate corrupted cache
            logger = structlog.get_logger()
            logger.warning("cache_decode_error", error=str(e), raw_type=type(raw).__name__, competition_slug_key=competition_slug_key)
            return None

    async def invalidate_catalog(self, category: str) -> None:
        """Invalidate competitions catalog for a specific category."""
        await self._r.delete(_key_catalog(category))

    async def invalidate_all(self) -> None:
        """Invalidate all competitions catalogs."""
        pattern = f"{KEY_PREFIX}:*"
        cursor = 0
        while True:
            cursor, keys = await self._r.scan(cursor, match=pattern, count=100)
            if keys:
                await self._r.delete(*keys)
            if cursor == 0:
                break
