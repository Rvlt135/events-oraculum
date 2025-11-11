"""
Pydantic schemas for Instructor validation.
"""
from typing import List
from pydantic import BaseModel, Field
from uuid import UUID


class EventPriorityScore(BaseModel):
    """Single event priority score."""
    event_id: UUID = Field(description="Event UUID")
    score: float = Field(ge=0.0, le=1.0, description="Priority score from 0.0 to 1.0")


class EventPriorityBatch(BaseModel):
    """Batch of event priority scores returned by LLM."""
    events: List[EventPriorityScore] = Field(
        description="List of events with their priority scores"
    )
