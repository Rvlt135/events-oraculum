from typing import Optional
from uuid import UUID

from pydantic import BaseModel

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
    event_id: Optional[UUID] = None
    competition_id: UUID
    season: int
    goal_probs_home: list[float]   # P(0), P(1), ... P(6)
    goal_probs_away: list[float]
    p_home: float
    p_draw: float
    p_away: float
    fair_home: float
    fair_draw: float
    fair_away: float