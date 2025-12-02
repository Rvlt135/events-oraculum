from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Float, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.infrastructure.db.orm.base import Base

class EventEdgeORM(Base):
    __tablename__ = "event_edges"

    event_id: UUID # (PK)
    competition_id: UUID
    season: int
    edges_json: JSONB   # serialized EventEdgeDTO
    created_at: datetime