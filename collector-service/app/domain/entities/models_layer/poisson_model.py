from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import UpcomingFixtureDTO


# TODO: scoped with EloInputFeaturesDTO
class PoissonInputFeaturesDTO(BaseModel):
    events: list[UpcomingFixtureDTO]
    team_features: dict[UUID, TeamFeaturesDTO]
    match_features: dict[UUID, MatchFeaturesDTO]
    poisson_features: dict[UUID, PoissonFeaturesDTO]

class PoissonModelDTO(BaseModel):
    """Poisson model output containing probabilities and fair odds.
    
    Does NOT include lambda values - those belong to PoissonFeaturesDTO (F3).
    """
    model_config = ConfigDict(extra="ignore")
    
    event_id: Optional[UUID] = None
    competition_id: Optional[UUID] = None
    season: Optional[int] = None
    goal_probs_home: Optional[list[float]] = None   # P(0), P(1), ... P(6)
    goal_probs_away: Optional[list[float]] = None
    p_home: Optional[float] = None
    p_draw: Optional[float] = None
    p_away: Optional[float] = None
    fair_home: Optional[float] = None
    fair_draw: Optional[float] = None
    fair_away: Optional[float] = None