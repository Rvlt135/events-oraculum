from typing import Optional

from pydantic import BaseModel, ConfigDict
from uuid import UUID


class PoissonFeaturesDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    event_id: Optional[UUID] = None
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

