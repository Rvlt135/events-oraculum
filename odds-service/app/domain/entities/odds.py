from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class BookmakerDTO(BaseModel):
    """DTO for Bookmaker entity."""
    id: UUID
    key: str
    name: str
    region: str
    is_active: bool
    created_at: datetime


class OddsOutcomeDTO(BaseModel):
    """DTO for odds outcome in snapshot."""
    name: str
    role: Literal["home", "away", "draw", "unknown"]
    team_id: UUID | None
    price: float
    provider_name: str | None = None
    sid: str | None = None
    bet_limit: dict | None = None


class OddsSnapshotDTO(BaseModel):
    """DTO for OddsSnapshot entity."""
    id: UUID | None = None
    event_id: UUID
    bookmaker_id: UUID
    market_type: str
    outcomes: list[OddsOutcomeDTO]
    timestamp_source: datetime
    timestamp_ingested: datetime
    created_at: datetime | None = None


class NormalizedOddsDTO(BaseModel):
    """DTO for NormalizedOdds entity."""
    id: UUID | None = None
    event_id: UUID
    market_type: str
    home_odds_avg: Decimal
    away_odds_avg: Decimal
    draw_odds_avg: Decimal | None
    home_odds_best: Decimal
    away_odds_best: Decimal
    draw_odds_best: Decimal | None
    bookmakers_count: int
    timestamp_source: datetime
    timestamp_ingested: datetime
    timestamp_normalized: datetime
    created_at: datetime | None = None


class ExternalOddsOutcomeDTO(BaseModel):
    name: str | None = None
    price: float | None = None
    link: str | None = None
    sid: str | None = None
    bet_limit: float | None = None

class ExternalOddsMarketDTO(BaseModel):
    key: str | None = None           # "h2h", "h2h_lay", "spreads", ...
    last_update: datetime | None = None
    link: str | None = None
    sid: str | None = None
    outcomes: list[ExternalOddsOutcomeDTO] = []

class ExternalOddsBookmakerDTO(BaseModel):
    key: str | None = None           # "onexbet"
    title: str | None = None         # "1xBet"
    last_update: datetime | None = None
    link: str | None = None          # ссылка на матч у букмекера
    sid: str | None = None           # internal id букмекера
    markets: list[ExternalOddsMarketDTO] = []

class ExternalOddsEventDTO(BaseModel):
    id: str | None = None
    sport_key: str | None = None
    sport_title: str | None = None
    commence_time: datetime | None = None
    home_team: str | None = None
    away_team: str | None = None
    home_rotation: str | None = None
    away_rotation: str | None = None
    bookmakers: list[ExternalOddsBookmakerDTO] = []

class EventBookmakerMarketOddsDTO(BaseModel):
   bookmaker: BookmakerDTO
   market_type: str            # ExternalOddsMarketDTO.key
   last_update: datetime | None
   outcomes: list[OddsOutcomeDTO]

class EventOddsDTO(BaseModel):
       event_id: UUID              # наш events.id
       external_id: str            # id провайдера
       provider_key: str           # sport_key / competition
       commence_time: datetime | None
       home_team: str | None
       away_team: str | None
       markets: list[EventBookmakerMarketOddsDTO]

class CompetitionOddsDTO(BaseModel):
       provider_key: str
       events: list[EventOddsDTO]


class EventShortDTO(BaseModel):
    """Short DTO for event identification in odds collection."""
    event_id: UUID
    external_id: str