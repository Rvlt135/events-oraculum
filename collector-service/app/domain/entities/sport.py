from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SportEntity(BaseModel):
    """Domain entity for Sport catalog entry."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    category: str
    plan_visibility: Literal["free", "pro", "unavailable"]
    is_active: bool

