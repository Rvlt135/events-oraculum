from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(Text, unique=True, nullable=False)
    sport_id = Column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="CASCADE"), nullable=False)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    commence_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Text, default="upcoming")
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sport = relationship("Sport", back_populates="events")
    competition = relationship("Competition", back_populates="events")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    odds_snapshots = relationship("OddsSnapshot", back_populates="event")
    normalized_odds = relationship("NormalizedOdds", back_populates="event")

    __table_args__ = (
        Index("idx_events_sport_id", "sport_id"),
        Index("idx_events_competition_id", "competition_id"),
        Index("idx_events_commence_time", "commence_time"),
        Index("idx_events_status", "status"),
        Index("idx_events_external_id", "external_id"),
    )