from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CompetitionEntity(BaseModel):
    """Domain entity for Competition catalog entry."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    sport_id: UUID
    provider: str
    provider_key: str
    title: str
    plan_visibility: Literal["free", "pro", "unavailable"]
    is_active: bool

