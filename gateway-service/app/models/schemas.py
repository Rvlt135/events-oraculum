from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class RecommendationDTO(BaseModel):
    rec_id: UUID
    event_id: UUID
    league_key: str
    pick: str
    confidence: float = Field(ge=0.0, le=1.0)
    short_explanation: str
    model_version: str
    created_ts: datetime

    class Config:
        from_attributes = True


class OddsContextDTO(BaseModel):
    home_odds_avg: Optional[float] = None
    away_odds_avg: Optional[float] = None
    draw_odds_avg: Optional[float] = None
    home_odds_best: Optional[float] = None
    away_odds_best: Optional[float] = None
    draw_odds_best: Optional[float] = None
    bookmakers_count: Optional[int] = None
    timestamp_source: Optional[datetime] = None


class EventDTO(BaseModel):
    event_id: UUID
    external_id: str
    league_key: str
    league_name: str
    home_team: str
    away_team: str
    commence_time: datetime
    status: str
    recommendations: List[RecommendationDTO] = Field(default_factory=list)
    odds_context: Optional[OddsContextDTO] = None


class StatsDTO(BaseModel):
    count_recommendations: int
    baseline_count: int
    distribution_by_pick: Dict[str, int]
    latest_recommendation_ts: Optional[datetime] = None
    period_from: Optional[datetime] = None
    period_to: Optional[datetime] = None
    league_key: Optional[str] = None


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[Any]
