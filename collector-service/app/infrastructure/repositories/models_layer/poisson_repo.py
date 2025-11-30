from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.models_layer.poisson_model import PoissonModelDTO
from app.infrastructure.db.orm.models_layer.poisson_model import PoissonModel
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class PoissonModelRepository(BaseRepository[PoissonModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(PoissonModel, session)

    async def bulk_upsert_poisson_model(
        self,
        outputs: list[PoissonModelDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Bulk upsert Poisson model predictions.
        
        Args:
            outputs: List of PoissonModelDTO records.
            competition_id: Competition ID.
            season: Season year.
            
        Returns:
            Number of processed records.
        """
        logger.debug("bulk_upsert_poisson_model_called", count=len(outputs))
        
        if not outputs:
            return 0
        
        values = [
            {
                "event_id": dto.event_id,
                "competition_id": competition_id,
                "season": season,
                "p_home": dto.p_home,
                "p_draw": dto.p_draw,
                "p_away": dto.p_away,
                "fair_home": dto.fair_home,
                "fair_draw": dto.fair_draw,
                "fair_away": dto.fair_away,
                "goal_probs_home": dto.goal_probs_home,
                "goal_probs_away": dto.goal_probs_away,
            }
            for dto in outputs
        ]
        
        stmt = insert(PoissonModel).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[PoissonModel.event_id],
            set_={
                "p_home": stmt.excluded.p_home,
                "p_draw": stmt.excluded.p_draw,
                "p_away": stmt.excluded.p_away,
                "fair_home": stmt.excluded.fair_home,
                "fair_draw": stmt.excluded.fair_draw,
                "fair_away": stmt.excluded.fair_away,
                "goal_probs_home": stmt.excluded.goal_probs_home,
                "goal_probs_away": stmt.excluded.goal_probs_away,
            }
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        logger.debug("bulk_upsert_poisson_model_completed", saved=len(outputs))
        return len(outputs)


    async def get_by_event_ids(
        self,
        event_ids: list[UUID],
        competition_id: UUID,
        season: int,
    ) -> dict[UUID, PoissonModelDTO]:
        """Get Poisson model predictions by event IDs.
        
        Args:
            event_ids: List of event identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Dictionary mapping event_id to PoissonModelDTO.
        """
        logger.debug("get_poisson_by_event_ids_called", count=len(event_ids), competition_id=str(competition_id), season=season)
        
        if not event_ids:
            return {}
        
        result = await self.session.execute(
            select(PoissonModel)
            .where(
                and_(
                    PoissonModel.event_id.in_(event_ids),
                    PoissonModel.competition_id == competition_id,
                    PoissonModel.season == season,
                )
            )
        )
        rows = result.scalars().all()
        
        models_dict = {}
        for row in rows:
            try:
                dto = PoissonModelDTO(
                    event_id=row.event_id,
                    competition_id=row.competition_id,
                    season=row.season,
                    goal_probs_home=row.goal_probs_home,
                    goal_probs_away=row.goal_probs_away,
                    p_home=row.p_home,
                    p_draw=row.p_draw,
                    p_away=row.p_away,
                    fair_home=row.fair_home,
                    fair_draw=row.fair_draw,
                    fair_away=row.fair_away,
                )
                models_dict[row.event_id] = dto
            except Exception as e:
                logger.warning("poisson_model_dto_creation_failed", event_id=str(row.event_id), error=str(e))
        
        logger.debug("get_poisson_by_event_ids_completed", count=len(models_dict))
        return models_dict