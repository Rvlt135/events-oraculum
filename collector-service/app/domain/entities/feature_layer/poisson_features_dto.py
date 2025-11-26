from pydantic import BaseModel
from uuid import UUID


class PoissonFeaturesDTO(BaseModel):
    fixture_id: UUID
    home_team_id: UUID
    away_team_id: UUID
    competition_id: UUID
    season: int
    lambda_home: float
    lambda_away: float
    home_strength: float
    away_strength: float
    expected_goals_home: float
    expected_goals_away: float

