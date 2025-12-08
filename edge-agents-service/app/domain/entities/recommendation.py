from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecommendationCreate(BaseModel):
    event_id: UUID
    league_key: str
    pick: str
    confidence: float = Field(ge=0.0, le=1.0)
    short_explanation: str
    reasoning: str
    model_version: str


class RecommendationSchema(BaseModel):
    pick: Literal["home", "draw", "away"] = Field(
        description="Recommended outcome: home win, draw, or away win"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level between 0.0 and 1.0"
    )
    short_explanation: str = Field(
        max_length=200,
        description="Brief reasoning for the recommendation (max 200 characters)"
    )
    reasoning: str = Field(
        description="Detailed explanation of why this event and outcome were selected"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "pick": "home",
                "confidence": 0.75,
                "short_explanation": "Strong home advantage with favorable odds",
                "reasoning": "• Home team undefeated in last 5 matches\n• Away team missing key striker\n• Historical H2H favors home (70% win rate)\n• Value in current odds (2.5 vs fair 2.1)"
            }
        }

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
