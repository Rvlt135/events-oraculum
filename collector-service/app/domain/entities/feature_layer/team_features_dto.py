from pydantic import BaseModel
from uuid import UUID

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import UpcomingFixtureDTO


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


# TODO: Duplicate PoissonInputFeaturesDTO for extract_features_scopes
class ScopesInputFeaturesDTO(BaseModel):
    events: list[UpcomingFixtureDTO]
    team_features: dict[UUID, TeamFeaturesDTO]
    match_features: dict[UUID, MatchFeaturesDTO]
    poisson_features: dict[UUID, PoissonFeaturesDTO]