from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import UpcomingFixtureDTO

# TODO: scoped with PoissonInputFeaturesDTO
class EloInputFeaturesDTO(BaseModel):
    events: list[UpcomingFixtureDTO]
    team_features: dict[UUID, TeamFeaturesDTO]
    match_features: dict[UUID, MatchFeaturesDTO]
    poisson_features: dict[UUID, PoissonFeaturesDTO]


class EloModelDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    event_id: Optional[UUID] = None
    elo_home_new: float
    elo_away_new: float
    expected_home: float
    expected_away: float
    draw_adjustment: float
    p_home: float
    p_draw: float
    p_away: float