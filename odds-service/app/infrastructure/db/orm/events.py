from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Text, Index, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider = Column(Text, nullable=False, default='odds_api')
    external_id = Column(Text, nullable=False)
    sport_id = Column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="CASCADE"), nullable=False)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)

    # Nullable team references for flexible participant support
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    home_team_name = Column(Text, nullable=True)
    away_team_name = Column(Text, nullable=True)

    commence_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Text, default="upcoming")

    # Participant mode and flexible participants storage
    participant_mode = Column(Text, nullable=False, default='unknown')
    participants = Column(JSONB, nullable=False, default=list)

    event_metadata = Column("event_metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ingested_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    sport = relationship("Sport", back_populates="events")
    competition = relationship("Competition", back_populates="events")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    odds_snapshots = relationship("OddsSnapshot", back_populates="event")
    normalized_odds = relationship("NormalizedOdds", back_populates="event")

    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_events_provider_external_id"),
        CheckConstraint(
            "participant_mode IN ('duel', 'solo', 'field', 'unknown')",
            name="chk_events_participant_mode"
        ),
        Index("idx_events_sport_id", "sport_id"),
        Index("idx_events_competition_id", "competition_id"),
        Index("idx_events_commence_time", "commence_time"),
        Index("idx_events_status", "status"),
        Index("idx_events_external_id", "external_id"),
        Index("idx_events_competition_commence", "competition_id", "commence_time"),
    )
