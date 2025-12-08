from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class RecommendationORM(Base):
    __tablename__ = "recommendations"

    rec_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    league_key = Column(String(100), nullable=False, index=True)
    pick = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    short_explanation = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    model_version = Column(String(50), nullable=False)
    created_ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)