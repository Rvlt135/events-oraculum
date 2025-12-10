from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# TODO: edges
class ValueCandidateDTO(BaseModel):
    selection: str   # "home" | "draw" | "away"
    fair_odds: float
    market_odds: float
    edge_percent: float


class EventEdgeDTO(BaseModel):
    event_id: UUID
    fair_home: float
    fair_draw: float
    fair_away: float
    edge_home: float
    edge_draw: float
    edge_away: float
    value_candidates: list[ValueCandidateDTO]

# TODO: bundles
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

class MatchFeaturesDTO(BaseModel):
    team_id: UUID
    competition_id: UUID
    season: int

    last_matches_count: int          # сколько матчей вошло в расчёт (<= N)

    goals_for_last_n: int            # суммарные голы GF за последние N
    goals_against_last_n: int        # суммарные GA за последние N
    goals_diff_last_n: int           # GF - GA

    wins_last_n: int                 # количество W
    draws_last_n: int                # количество D
    losses_last_n: int               # количество L

    avg_goals_for_last_n: float      # goals_for_last_n / last_matches_count
    avg_goals_against_last_n: float  # goals_against_last_n / last_matches_count

    form_last_n: str                 # строка: "WDLWD"


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


class PoissonModelDTO(BaseModel):
    """Poisson model output containing probabilities and fair odds.

    Does NOT include lambda values - those belong to PoissonFeaturesDTO (F3).
    """
    model_config = ConfigDict(extra="ignore")

    event_id: Optional[UUID] = None
    competition_id: Optional[UUID] = None
    season: Optional[int] = None
    goal_probs_home: Optional[list[float]] = None  # P(0), P(1), ... P(6)
    goal_probs_away: Optional[list[float]] = None
    p_home: Optional[float] = None
    p_draw: Optional[float] = None
    p_away: Optional[float] = None
    fair_home: Optional[float] = None
    fair_draw: Optional[float] = None
    fair_away: Optional[float] = None

class MarketOddsDTO(BaseModel):
    market_type: str                   # example: "h2h"
    home_avg: float
    away_avg: float
    draw_avg: float | None
    home_best: float
    away_best: float
    draw_best: float | None
    bookmakers_count: int

class EventFeatureBundleDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

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

    def to_clean_dict(self) -> dict:  # TODO: remove this method after delete event_id in nested models
        """Convert bundle to dict with nested event_id fields removed.

        This method produces a clean bundle_json for storage (DB/cache)
        by removing redundant event_id fields from nested objects.
        The root event_id is preserved.

        Returns:
            Dictionary representation with nested event_id fields removed.
        """
        data = self.model_dump(mode="json", exclude_none=True)

        # Remove nested event_id fields if present
        for key in ["elo_output", "poisson_output", "poisson_event_features"]:
            if key in data and isinstance(data[key], dict):
                data[key].pop("event_id", None)

        return data