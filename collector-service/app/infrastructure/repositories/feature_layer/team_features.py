from typing import List
from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.infrastructure.db.orm.feature_layer.team_features import TeamFeatures
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


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

    async def get_by_team_ids(self, team_ids: set[UUID], competition_id: UUID, season: int) -> dict[UUID, TeamFeaturesDTO]:
        """Get team features by team IDs, competition and season.
        
        Args:
            team_ids: Set of team identifiers.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Dictionary mapping team_id to TeamFeaturesDTO.
        """
        logger.debug("team_features_get_by_team_ids_called", competition_id=str(competition_id), season=season, team_ids_count=len(team_ids))
        if not team_ids:
            return {}
        
        result = await self.session.execute(
            select(TeamFeatures)
            .where(and_(
                TeamFeatures.team_id.in_(team_ids),
                TeamFeatures.competition_id == competition_id,
                TeamFeatures.season == season
            ))
        )
        rows = result.scalars().all()
        features_dict = {
            row.team_id: TeamFeaturesDTO(
                team_id=row.team_id,
                competition_id=row.competition_id,
                season=row.season,
                strength_initial=row.strength_initial,
                form_score=row.form_score,
                goals_for_avg=row.goals_for_avg,
                goals_against_avg=row.goals_against_avg,
                goal_diff=row.goal_diff,
                games_played=row.games_played,
            )
            for row in rows
        }
        logger.debug("team_features_get_by_team_ids_result", fetched_count=len(features_dict))
        return features_dict
