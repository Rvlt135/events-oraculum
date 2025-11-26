from pydantic import BaseModel
from uuid import UUID


class TeamFeaturesDTO(BaseModel):
    team_id: UUID
    competition_id: UUID
    season: int
    strength_initial: float
    form_score: float
    goals_for_avg: float
    goals_against_avg: float
    goal_diff: int
    games_played: int