from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.infrastructure.db.orm.feature_layer.match_features import MatchFeatures
from app.infrastructure.repositories.base import BaseRepository


class MatchFeaturesRepository(BaseRepository[MatchFeatures]):
    def __init__(self, session: AsyncSession):
        super().__init__(MatchFeatures, session)


    async def bulk_upsert_match_features(self, features: list[MatchFeaturesDTO]) -> int:
        """
        Bulk upsert match features.
        
        Args:
            features: List of MatchFeaturesDTO records
        """
        if not features:
            return 0
        
        values = [
            {
                "team_id": f.team_id,
                "competition_id": f.competition_id,
                "season": f.season,
                "last_matches_count": f.last_matches_count,
                "goals_for_last_n": f.goals_for_last_n,
                "goals_against_last_n": f.goals_against_last_n,
                "goals_diff_last_n": f.goals_diff_last_n,
                "wins_last_n": f.wins_last_n,
                "draws_last_n": f.draws_last_n,
                "losses_last_n": f.losses_last_n,
                "avg_goals_for_last_n": f.avg_goals_for_last_n,
                "avg_goals_against_last_n": f.avg_goals_against_last_n,
                "form_last_n": f.form_last_n,
            }
            for f in features
        ]
        
        stmt = insert(MatchFeatures).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_match_features_team_competition_season",
            set_={
                "last_matches_count": stmt.excluded.last_matches_count,
                "goals_for_last_n": stmt.excluded.goals_for_last_n,
                "goals_against_last_n": stmt.excluded.goals_against_last_n,
                "goals_diff_last_n": stmt.excluded.goals_diff_last_n,
                "wins_last_n": stmt.excluded.wins_last_n,
                "draws_last_n": stmt.excluded.draws_last_n,
                "losses_last_n": stmt.excluded.losses_last_n,
                "avg_goals_for_last_n": stmt.excluded.avg_goals_for_last_n,
                "avg_goals_against_last_n": stmt.excluded.avg_goals_against_last_n,
                "form_last_n": stmt.excluded.form_last_n,
            }
        )
        
        await self.session.execute(stmt)
        return len(values)
    