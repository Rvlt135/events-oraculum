"""
Pydantic schemas for LLM function calling validation.
"""
from typing import List
from pydantic import BaseModel, Field, RootModel
from uuid import UUID


class EventPriorityScore(BaseModel):
    """Single event priority score."""
    event_id: UUID = Field(description="Event UUID")
    priority: float = Field(ge=0.0, le=1.0, description="Priority score from 0.0 to 1.0")


class EventPriorityBatch(RootModel[List[EventPriorityScore]]):
    """Batch of event priority scores returned by LLM as a JSON array."""
    root: List[EventPriorityScore] = Field(
        description="List of events with their priority scores"
    )
    
    @property
    def events(self) -> List[EventPriorityScore]:
        """Alias for root to maintain backward compatibility."""
        return self.root
