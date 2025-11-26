from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, SmallInteger, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.infrastructure.db.orm.base import Base


class TeamFeatures(Base):
    """Team features model for feature layer"""
    __tablename__ = "team_features"