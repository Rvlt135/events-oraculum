from datetime import datetime
from typing import Literal, Dict, Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class SeasonsDto(BaseModel):
    current: Optional[int] = None
    previous: Optional[int] = None

class ApiSourceDto(BaseModel):
    seasons: Optional[SeasonsDto] = None
    league_id: Optional[int] = None

class CompetitionReadDTO(BaseModel):
    """Domain entity for Competition catalog entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sport_id: UUID
    title: str
    slug_key: str
    plan_visibility: Literal["free", "pro", "unavailable"]
    is_active: bool
    api_sources: Optional[ApiSourceDto] = Field(default_factory=ApiSourceDto)

class CompetitionResponse(BaseModel):
    competitions: List[CompetitionReadDTO]

class UpcomingEventCatalogDTO(BaseModel):
    """Simplified DTO for upcoming events catalog without market odds."""
    event_id: UUID
    competition_id: UUID
    season: int
    home_id: UUID
    away_id: UUID
    date: datetime


class UpcomingEventCatalogResponse(BaseModel):
    events: List[UpcomingEventCatalogDTO]