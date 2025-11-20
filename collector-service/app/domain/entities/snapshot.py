from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from app.utils.time_utils import now_utc
from app.domain.enums import SportType, MarketType


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
