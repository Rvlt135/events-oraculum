from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SportType(str, Enum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"


class MarketType(str, Enum):
    H2H = "h2h"
    SPREADS = "spreads"
    TOTALS = "totals"


class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Team(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    normalized_name: str
    external_id: str | None = None


class Quote(BaseModel):
    bookmaker: str
    bookmaker_key: str
    odds: float
    timestamp_source: datetime
    timestamp_ingested: datetime
    last_updated: datetime | None = None


class Market(BaseModel):
    market_type: MarketType
    outcomes: dict[str, list[Quote]]


class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    external_id: str
    sport_type: SportType
    league: str
    home_team: str
    away_team: str
    commence_time: datetime
    status: EventStatus = EventStatus.UPCOMING
    markets: dict[str, Market] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NormalizedEvent(BaseModel):
    event_id: UUID
    external_id: str
    sport: SportType
    league: str
    home_team: str
    away_team: str
    commence_time: datetime
    market_type: MarketType
    home_odds_avg: float
    away_odds_avg: float
    draw_odds_avg: float | None = None
    home_odds_best: float
    away_odds_best: float
    draw_odds_best: float | None = None
    bookmakers_count: int
    timestamp_normalized: datetime = Field(default_factory=datetime.utcnow)
