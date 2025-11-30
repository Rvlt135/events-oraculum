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
from app.domain.entities.models_layer.poisson_model import PoissonModelDTO

MODEL_TTL_SEC = settings.cache_ttl_models_layer_sec
KEY_PREFIX_ELO = "elo:model"
KEY_PREFIX_POISSON = "poisson:model"

logger = structlog.get_logger()

class ModelsLayerCache:
    """Redis cache layer for team features"""

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    def _key_elo_events(self, event_id: UUID, competition_id: UUID, season: int) -> str:
        """Generate Redis key for team features."""
        return f"{KEY_PREFIX_ELO}:event:{event_id}:{competition_id}:{season}"

    def _key_poisson_events(self, event_id: UUID, competition_id: UUID, season: int) -> str:
        """Generate Redis key for Poisson model events."""
        return f"{KEY_PREFIX_POISSON}:event:{event_id}:{competition_id}:{season}"


    async def save_elo_events(self, elo_outputs: list[EloModelDTO], competition_id: UUID, season: int, ttl: int = MODEL_TTL_SEC) -> int:
        """Store Elo model outputs in Redis.
        
        Args:
            elo_outputs: List of EloModelDTO records.
            competition_id: Competition ID.
            season: Season.
            ttl: TTL in seconds.
        Returns:
            Number of items saved.
        """
        if not elo_outputs:
            return 0
        
        async with self._r.pipeline() as pipe:
            for dto in elo_outputs:
                # Note: EloModelDTO doesn't have competition_id and season,
                # so using event_id only in the key
                key = self._key_elo_events(dto.event_id, competition_id, season)
                
                payload = {
                    "p_home": dto.p_home,
                    "p_draw": dto.p_draw,
                    "p_away": dto.p_away,
                    "expected_home": dto.expected_home,
                    "expected_away": dto.expected_away,
                    "draw_adjustment": dto.draw_adjustment,
                    "elo_home_new": dto.elo_home_new,
                    "elo_away_new": dto.elo_away_new,
                }
                json_payload = json.dumps(payload, ensure_ascii=False)
                await pipe.set(key, json_payload, ttl)
            await pipe.execute()
        
        logger.debug("elo_cache_saved", count=len(elo_outputs))
        return len(elo_outputs)

    async def save_poisson_events(
        self,
        outputs: list[PoissonModelDTO],
        competition_id: UUID,
        season: int,
        ttl: int = MODEL_TTL_SEC,
    ) -> int:
        """Store Poisson model outputs in Redis.
        
        Args:
            outputs: List of PoissonModelDTO records.
            competition_id: Competition ID.
            season: Season year.
            ttl: TTL in seconds.
            
        Returns:
            Number of items saved.
        """
        logger.debug("poisson_cache_save_started", count=len(outputs))
        
        if not outputs:
            return 0
        
        saved_count = len(outputs)
        
        async with self._r.pipeline() as pipe:
            for dto in outputs:
                key = self._key_poisson_events(dto.event_id, competition_id, season)
                
                value = {
                    "p_home": dto.p_home,
                    "p_draw": dto.p_draw,
                    "p_away": dto.p_away,
                    "fair_home": dto.fair_home,
                    "fair_draw": dto.fair_draw,
                    "fair_away": dto.fair_away,
                    "goal_probs_home": dto.goal_probs_home,
                    "goal_probs_away": dto.goal_probs_away,
                }
                json_value = json.dumps(value, ensure_ascii=False)
                await pipe.set(key, json_value, ex=ttl)
            await pipe.execute()
        
        logger.debug("poisson_cache_save_completed", saved=saved_count)
        return saved_count

    def _deserialize_elo_model(self, raw_value: Optional[str], event_id: UUID) -> Optional[EloModelDTO]:
        """Deserialize raw JSON string to EloModelDTO.
        
        Args:
            raw_value: Raw JSON string from cache or None.
            event_id: Event ID to include in DTO.
            
        Returns:
            EloModelDTO if valid, None otherwise.
        """
        if not raw_value:
            return None
        
        try:
            data = json.loads(raw_value)
            data["event_id"] = event_id
            return EloModelDTO(**data)
        except Exception as e:
            logger.warning("elo_cache_deserialize_error", event_id=str(event_id), error=str(e))
            return None

    def _deserialize_poisson_model(
        self,
        raw_value: Optional[str],
        event_id: UUID,
        competition_id: UUID,
        season: int,
    ) -> Optional[PoissonModelDTO]:
        """Deserialize raw JSON string to PoissonModelDTO.
        
        Args:
            raw_value: Raw JSON string from cache or None.
            event_id: Event ID to include in DTO.
            competition_id: Competition ID to include in DTO.
            season: Season to include in DTO.
            
        Returns:
            PoissonModelDTO if valid, None otherwise.
        """
        if not raw_value:
            return None
        
        try:
            data = json.loads(raw_value)
            data["event_id"] = event_id
            data["competition_id"] = competition_id
            data["season"] = season
            return PoissonModelDTO(**data)
        except Exception as e:
            logger.warning("poisson_cache_deserialize_error", event_id=str(event_id), error=str(e))
            return None

    async def get_elo_by_event_ids(
        self,
        event_ids: list[UUID],
        competition_id: UUID,
        season: int,
    ) -> dict[UUID, EloModelDTO]:
        """Get Elo model predictions from cache by event IDs.
        
        Args:
            event_ids: List of event identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Dictionary mapping event_id to EloModelDTO (cache hits only).
        """
        logger.debug("get_elo_by_event_ids_called", count=len(event_ids))
        
        if not event_ids:
            return {}
        
        async with self._r.pipeline() as pipe:
            for event_id in event_ids:
                key = self._key_elo_events(event_id, competition_id, season)
                await pipe.get(key)
            raw_values = await pipe.execute()
        
        result = {}
        for event_id, raw_value in zip(event_ids, raw_values):
            dto = self._deserialize_elo_model(raw_value, event_id)
            if dto is not None:
                result[event_id] = dto
        
        logger.debug("get_elo_by_event_ids_completed", total=len(result))
        return result

    async def get_poisson_by_event_ids(
        self,
        event_ids: list[UUID],
        competition_id: UUID,
        season: int,
    ) -> dict[UUID, PoissonModelDTO]:
        """Get Poisson model predictions from cache by event IDs.
        
        Args:
            event_ids: List of event identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Dictionary mapping event_id to PoissonModelDTO (cache hits only).
        """
        logger.debug("get_poisson_by_event_ids_called", count=len(event_ids))
        
        if not event_ids:
            return {}
        
        async with self._r.pipeline() as pipe:
            for event_id in event_ids:
                key = self._key_poisson_events(event_id, competition_id, season)
                await pipe.get(key)
            raw_values = await pipe.execute()
        
        result = {}
        for event_id, raw_value in zip(event_ids, raw_values):
            dto = self._deserialize_poisson_model(raw_value, event_id, competition_id, season)
            if dto is not None:
                result[event_id] = dto
        
        logger.debug("get_poisson_by_event_ids_completed", total=len(result))
        return result