from typing import List
from uuid import UUID
import structlog
from sqlalchemy import select, and_
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
            competition_id: Competition ID.
            season: Season.
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


    async def get_by_event_ids(
        self,
        event_ids: list[UUID],
        competition_id: UUID,
        season: int,
    ) -> dict[UUID, EloModelDTO]:
        """Get Elo model predictions by event IDs.
        
        Args:
            event_ids: List of event identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Dictionary mapping event_id to EloModelDTO.
        """
        logger.debug("get_elo_by_event_ids_called", count=len(event_ids), competition_id=str(competition_id), season=season)
        
        if not event_ids:
            return {}
        
        result = await self.session.execute(
            select(EloModel)
            .where(
                and_(
                    EloModel.event_id.in_(event_ids),
                    EloModel.competition_id == competition_id,
                    EloModel.season == season,
                )
            )
        )
        rows = result.scalars().all()
        
        models_dict = {}
        for row in rows:
            try:
                dto = EloModelDTO(
                    event_id=row.event_id,
                    elo_home_new=row.elo_home_new,
                    elo_away_new=row.elo_away_new,
                    expected_home=row.expected_home,
                    expected_away=row.expected_away,
                    draw_adjustment=row.draw_adjustment,
                    p_home=row.p_home,
                    p_draw=row.p_draw,
                    p_away=row.p_away,
                )
                models_dict[row.event_id] = dto
            except Exception as e:
                logger.warning("elo_model_dto_creation_failed", event_id=str(row.event_id), error=str(e))
        
        logger.debug("get_elo_by_event_ids_completed", count=len(models_dict))
        return models_dict