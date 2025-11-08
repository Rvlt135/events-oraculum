from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from app.utils.time_utils import now_utc
from app.domain.enums import SportType, Market, EventStatus

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