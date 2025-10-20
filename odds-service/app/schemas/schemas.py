from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class Provider(str, Enum):
    THE_ODDS_API = "the_odds_api"


class Region(str, Enum):
    EU = "eu"
    US = "us"
    UK = "uk"
    AU = "au"


class Market(str, Enum):
    H2H = "h2h"
    SPREADS = "spreads"
    TOTALS = "totals"


class SportType(str, Enum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    HOCKEY = "hockey"


class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    sport_key: str
    sport_title: str
    home_team: str
    away_team: str
    commence_time_utc: datetime

    @field_serializer("commence_time_utc")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            from app.domain.time_utils import ensure_utc
            dt = ensure_utc(dt)
        return dt.isoformat().replace("+00:00", "Z")


class BookmakerOdds(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bookmaker: str
    last_update_utc: datetime
    home: Optional[float] = None
    draw: Optional[float] = None
    away: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

    @field_serializer("last_update_utc")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            from app.domain.time_utils import ensure_utc
            dt = ensure_utc(dt)
        return dt.isoformat().replace("+00:00", "Z")


class OddsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event: EventRef
    provider: Provider
    market: Market
    odds: List[BookmakerOdds]
    fetched_at_utc: datetime

    @field_serializer("fetched_at_utc")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            from app.domain.time_utils import ensure_utc
            dt = ensure_utc(dt)
        return dt.isoformat().replace("+00:00", "Z")


class OddsQuery(BaseModel):
    sport_key: str
    regions: List[Region] = Field(default=[Region.EU])
    markets: List[Market] = Field(default=[Market.H2H])
    date_from_utc: Optional[datetime] = None
    date_to_utc: Optional[datetime] = None
    bookmakers: Optional[List[str]] = None
    include_closed: bool = False


class PaginationQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    order_by: Optional[str] = None


class OddsResponse(BaseModel):
    items: List[OddsItem]
    total: int
    next_cursor: Optional[str] = None


class SnapshotSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    external_id: str
    # sport: str
    league: str = Field(alias="league_key")
    home_team: str
    away_team: str
    commence_time: datetime
    market_type: str
    home_odds_avg: float
    away_odds_avg: float
    draw_odds_avg: Optional[float] = None
    home_odds_best: float
    away_odds_best: float
    draw_odds_best: Optional[float] = None
    bookmakers_count: int
    ts_src: datetime = Field(alias="timestamp_source")  # Маппинг
    ts_ingest: datetime = Field(alias="timestamp_ingested")  # Маппинг
    ts_normalized: datetime = Field(alias="timestamp_normalized")

    @field_serializer("commence_time", "ts_src", "ts_ingest", "ts_normalized")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            from app.domain.time_utils import ensure_utc
            dt = ensure_utc(dt)
        return dt.isoformat().replace("+00:00", "Z")


class SnapshotsResponse(BaseModel):
    count: int
    limit: int
    league: Optional[str]
    snapshots: List[SnapshotSummary]


class TaskTriggerResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str


class ServiceInfoResponse(BaseModel):
    service: str
    version: str
    status: str
    environment: str
