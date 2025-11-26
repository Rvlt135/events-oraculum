from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.infrastructure.db.orm.feature_layer.team_features import TeamFeatures
from app.infrastructure.repositories.base import BaseRepository


class TeamFeaturesRepository(BaseRepository[TeamFeatures]):
    def __init__(self, session: AsyncSession):
        super().__init__(TeamFeatures, session)

    async def bulk_upsert_team_features(self, features: List[TeamFeaturesDTO]) -> int:
        """
        Bulk upsert team features.
        
        Args:
            features: List of TeamFeaturesDTO records
            
        Returns:
            Number of processed records
        """
        if not features:
            return 0
        
        values = [
            {
                "team_id": f.team_id,
                "competition_id": f.competition_id,
                "season": f.season,
                "strength_initial": f.strength_initial,
                "form_score": f.form_score,
                "goals_for_avg": f.goals_for_avg,
                "goals_against_avg": f.goals_against_avg,
                "goal_diff": f.goal_diff,
                "games_played": f.games_played,
            }
            for f in features
        ]
        
        stmt = insert(TeamFeatures).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_team_features_team_competition_season",
            set_={
                "strength_initial": stmt.excluded.strength_initial,
                "form_score": stmt.excluded.form_score,
                "goals_for_avg": stmt.excluded.goals_for_avg,
                "goals_against_avg": stmt.excluded.goals_against_avg,
                "goal_diff": stmt.excluded.goal_diff,
                "games_played": stmt.excluded.games_played,
            }
        )
        
        await self.session.execute(stmt)
        return len(values)
