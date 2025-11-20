from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from decimal import Decimal


class EventPriorityDTO(BaseModel):
    """DTO for event priority data."""
    id: UUID
    provider: str
    provider_key: str
    event_id: UUID
    priority: Decimal = Field(..., decimal_places=3, max_digits=4)
    model: str
    evaluated_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

