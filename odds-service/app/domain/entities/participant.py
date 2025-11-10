"""
Domain entities for event participants.
"""
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class ParticipantItemDTO(BaseModel):
    """DTO for single participant in an event."""
    role: Literal["home", "away", "solo", "field"]
    name: str
    provider_alias: str
    team_id: Optional[UUID] = None


class EventUpsertDTO(BaseModel):
    """DTO for creating or updating an event with flexible participants."""
    provider: str = "odds_api"
    external_id: str
    sport_id: UUID
    competition_id: UUID

    # Optional team references
    home_team_id: Optional[UUID] = None
    away_team_id: Optional[UUID] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None

    commence_time: str  # ISO datetime string
    status: str = "upcoming"

    # Participant information
    participant_mode: Literal["duel", "solo", "field", "unknown"] = "unknown"
    participants: list[ParticipantItemDTO] = []

    metadata: dict = {}
