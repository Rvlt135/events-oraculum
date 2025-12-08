from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

class RecommendationResponse(BaseModel):
    rec_id: UUID
    event_id: UUID
    league_key: str
    pick: str
    confidence: float
    short_explanation: str
    reasoning: str
    model_version: str
    created_ts: datetime


    model_config = ConfigDict(from_attributes=True)
    # class Config:
    #     from_attributes = True
