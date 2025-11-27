from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Index, func
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.db.orm.base import Base


class FixturesFootballUpcoming(Base):
    """Upcoming fixtures for Poisson features computation."""
    __tablename__ = "fixtures_football_upcoming"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    """Primary key identifier."""
    event_id = Column(UUID(as_uuid=True), nullable=True)
    """Optional reference to events table."""
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    """Reference to the competition."""
    season = Column(Integer, nullable=False)
    """Season year."""
    match_date = Column(DateTime(timezone=True), nullable=False)
    """Match date and time."""
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    """Reference to the home team."""
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    """Reference to the away team."""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """Timestamp when the record was created."""

    __table_args__ = (
        Index("idx_fixtures_football_upcoming_competition_season", "competition_id", "season"),
        Index("idx_fixtures_football_upcoming_match_date", "match_date"),
    )

