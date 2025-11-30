from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.models_layer.dto import ModelScopesDTO
from app.domain.entities.models_layer.elo_model import EloModelDTO
from app.domain.entities.models_layer.poisson_model import PoissonModelDTO
from app.domain.entities.statistics.dto.fixtures_dto import UpcomingFixtureDTO


class MarketOddsDTO(BaseModel):
    market_type: str                   # example: "h2h"
    home_avg: float
    away_avg: float
    draw_avg: float | None
    home_best: float
    away_best: float
    draw_best: float | None
    bookmakers_count: int
    # timestamp_source: datetime
    # timestamp_ingested: datetime
    # timestamp_normalized: datetime

class UpcomingEventDTO(BaseModel):
    event_id: UUID
    home_team_id: UUID
    away_team_id: UUID
    match_date: datetime      # = UpcomingFixtureDTO.match_date
    competition_id: UUID
    season: int
    market_odds: MarketOddsDTO

class EventLayerBuildInputDTO(BaseModel):
    events: list[UpcomingEventDTO]
    team_features: dict[UUID, TeamFeaturesDTO]
    match_features: dict[UUID, MatchFeaturesDTO]
    poisson_features: dict[UUID, PoissonFeaturesDTO]
    model_outputs: ModelScopesDTO # TODO: не понятно что здесь должно быть

class EventFeatureBundleDTO(BaseModel):
    event_id: UUID

    home_team: TeamFeaturesDTO
    away_team: TeamFeaturesDTO

    match_history_home: MatchFeaturesDTO
    match_history_away: MatchFeaturesDTO

    poisson_event_features: PoissonFeaturesDTO

    elo_output: EloModelDTO
    poisson_output: PoissonModelDTO

    market_odds: MarketOddsDTO
    match_date: datetime
