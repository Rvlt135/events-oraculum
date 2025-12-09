from typing import Literal, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CompetitionEntity(BaseModel):
    """Domain entity for Competition catalog entry."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    sport_id: UUID
    description: Optional[str] = None
    provider: str
    slug_key: str
    title: str
    category: str
    plan_visibility: Literal["free", "pro", "unavailable"]
    is_active: bool
    api_sources: Dict[str, Any] = Field(default_factory=dict)


class CompetitionReadDTO(BaseModel):
    """Domain entity for Competition catalog entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sport_id: UUID
    title: str
    slug_key: str
    plan_visibility: Literal["free", "pro", "unavailable"]
    is_active: bool
    api_sources: Dict[str, Any] = Field(default_factory=dict)


