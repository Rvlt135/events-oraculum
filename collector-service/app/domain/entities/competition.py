from typing import Literal, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CompetitionEntity(BaseModel):
    """Domain entity for Competition catalog entry."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    sport_id: UUID
    provider: str
    slug_key: str
    title: str
    plan_visibility: Literal["free", "pro", "unavailable"]
    is_active: bool
    api_sources: Dict[str, Any] = Field(default_factory=dict)

