from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Float, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.infrastructure.db.orm.base import Base


class EventFeatureBundleORM(Base):
    """Event feature bundle model."""
    __tablename__ = "event_feature_bundles"

    event_id = Column(UUID, primary_key=True)
    competition_id = Column(UUID, index=True)
    season = Column(Integer, index=True)
    bundle_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now())