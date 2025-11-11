from datetime import datetime
from typing import Any, Dict, Optional
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


class EventDTO(BaseModel):
    """DTO for event data used in cache and responses."""
    id: UUID
    provider: str
    external_id: str
    sport_id: UUID
    competition_id: UUID
    home_team_id: Optional[UUID] = None
    away_team_id: Optional[UUID] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    commence_time: datetime
    status: str = "planned"
    participant_mode: str = "unknown"
    participants: list[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    ingested_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    @property
    def is_elapsed(self) -> bool:
        """Check if event has already commenced."""
        return self.commence_time < now_utc()

    def make(self):
        pass
