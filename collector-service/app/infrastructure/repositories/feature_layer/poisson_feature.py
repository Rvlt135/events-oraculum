from typing import List
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.db.orm.feature_layer.poisson_features import PoissonFeatures

logger = structlog.get_logger()

class PoissonFeatureRepository(BaseRepository[PoissonFeatures]):
    def __init__(self, session: AsyncSession):
        super().__init__(PoissonFeatures, session)

    async def bulk_upsert_poisson_features(self, features: list[PoissonFeaturesDTO]) -> int:
        """Bulk upsert poisson features.
        
        Args:
            features: List of PoissonFeaturesDTO records.
            
        Returns:
            Number of processed records.
        """
        logger.debug("bulk_upsert_poisson_features_called", items_count=len(features))
        if not features:
            logger.debug("bulk_upsert_poisson_features_empty")
            return 0
        
        values = [
            {
                "event_id": f.event_id,
                "home_team_id": f.home_team_id,
                "away_team_id": f.away_team_id,
                "competition_id": f.competition_id,
                "season": f.season,
                "lambda_home": f.lambda_home,
                "lambda_away": f.lambda_away,
                "home_strength": f.home_strength,
                "away_strength": f.away_strength,
                "expected_goals_home": f.expected_goals_home,
                "expected_goals_away": f.expected_goals_away,
            }
            for f in features
        ]
        
        stmt = insert(PoissonFeatures).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_poisson_features_event_id",
            set_={
                "lambda_home": stmt.excluded.lambda_home,
                "lambda_away": stmt.excluded.lambda_away,
                "home_strength": stmt.excluded.home_strength,
                "away_strength": stmt.excluded.away_strength,
                "expected_goals_home": stmt.excluded.expected_goals_home,
                "expected_goals_away": stmt.excluded.expected_goals_away,
                "competition_id": stmt.excluded.competition_id,
                "season": stmt.excluded.season,
                "home_team_id": stmt.excluded.home_team_id,
                "away_team_id": stmt.excluded.away_team_id,
            }
        )
        
        await self.session.execute(stmt)
        affected_count = len(values)
        logger.info("bulk_upsert_poisson_features_completed", affected_count=affected_count)
        return affected_count