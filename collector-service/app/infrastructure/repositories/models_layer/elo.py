from typing import List
from uuid import UUID
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.models_layer.elo_model import EloModelDTO
from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.db.orm.models_layer.elo_model import EloModel

logger = structlog.get_logger()

class EloRepository(BaseRepository[EloModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(EloModel, session)

    async def bulk_upsert_elo_model(self, elo_outputs: list[EloModelDTO], competition_id: UUID, season: int) -> int:
        """Bulk upsert Elo model predictions.
        
        Args:
            elo_outputs: List of EloModelDTO records.
            
        Returns:
            Number of processed records.
        """
        logger.debug("elo_bulk_upsert_started", count=len(elo_outputs))
        if not elo_outputs:
            return 0
        
        values = [
            {
                "event_id": dto.event_id,
                "competition_id": competition_id,
                "season": season,
                "p_home": dto.p_home,
                "p_draw": dto.p_draw,
                "p_away": dto.p_away,
                "expected_home": dto.expected_home,
                "expected_away": dto.expected_away,
                "draw_adjustment": dto.draw_adjustment,
                "elo_home_new": dto.elo_home_new,
                "elo_away_new": dto.elo_away_new,
            }
            for dto in elo_outputs
        ]
        
        stmt = insert(EloModel).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[EloModel.event_id],
            set_={
                "p_home": stmt.excluded.p_home,
                "p_draw": stmt.excluded.p_draw,
                "p_away": stmt.excluded.p_away,
                "expected_home": stmt.excluded.expected_home,
                "expected_away": stmt.excluded.expected_away,
                "draw_adjustment": stmt.excluded.draw_adjustment,
                "elo_home_new": stmt.excluded.elo_home_new,
                "elo_away_new": stmt.excluded.elo_away_new,
            }
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        logger.debug("elo_bulk_upsert_completed", count=len(elo_outputs))
        return len(elo_outputs)