from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel, Field


class Base(DeclarativeBase):
    pass


class RecommendationDB(Base):
    __tablename__ = "recommendations"

    rec_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    league_key = Column(String(100), nullable=False, index=True)
    pick = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    short_explanation = Column(Text, nullable=False)
    model_version = Column(String(50), nullable=False)
    created_ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class RecommendationCreate(BaseModel):
    event_id: UUID
    league_key: str
    pick: str
    confidence: float = Field(ge=0.0, le=1.0)
    short_explanation: str
    model_version: str


class RecommendationResponse(BaseModel):
    rec_id: UUID
    event_id: UUID
    league_key: str
    pick: str
    confidence: float
    short_explanation: str
    model_version: str
    created_ts: datetime

    class Config:
        from_attributes = True
