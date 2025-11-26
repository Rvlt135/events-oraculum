from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from app.domain.utils.time_utils import now_utc


class SportType(str, Enum):
    FOOTBALL = "football"


class MarketType(str, Enum):
    H2H = "h2h"


class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Quote(BaseModel):
    bookmaker: str
    bookmaker_key: str
    odds: float
    ts_src: datetime
    ts_ingest: datetime


class Market(BaseModel):
    market_type: MarketType
    outcomes: Dict[str, List[Quote]]


class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    external_id: str
    sport_type: SportType
    competition: str
    home_team: str
    away_team: str
    commence_time: datetime
    status: EventStatus = EventStatus.UPCOMING
    markets: Dict[str, Market] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class NormalizedSnapshot(BaseModel):
    event_id: UUID
    external_id: str
    sport: SportType
    competition: str
    home_team: str
    away_team: str
    commence_time: datetime
    market_type: MarketType
    home_odds_avg: float
    away_odds_avg: float
    draw_odds_avg: Optional[float] = None
    home_odds_best: float
    away_odds_best: float
    draw_odds_best: Optional[float] = None
    bookmakers_count: int
    ts_src: datetime
    ts_ingest: datetime
    ts_normalized: datetime = Field(default_factory=now_utc)
