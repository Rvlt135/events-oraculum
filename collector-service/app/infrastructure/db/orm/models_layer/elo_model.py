from sqlalchemy import Column, DateTime, ForeignKey, Integer, Float, Index, func
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.db.orm.base import Base


class EloModel(Base):
    """Elo model predictions for events."""
    __tablename__ = "elo_model"

    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    """Primary key and reference to the event."""
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    """Reference to the competition."""
    season = Column(Integer, nullable=False)
    """Season year."""
    p_home = Column(Float, nullable=False)
    """Probability of home team win."""
    p_draw = Column(Float, nullable=False)
    """Probability of draw."""
    p_away = Column(Float, nullable=False)
    """Probability of away team win."""
    expected_home = Column(Float, nullable=False)
    """Expected result for home team."""
    expected_away = Column(Float, nullable=False)
    """Expected result for away team."""
    draw_adjustment = Column(Float, nullable=False)
    """Draw probability adjustment."""
    elo_home_new = Column(Float, nullable=False)
    """New Elo rating for home team."""
    elo_away_new = Column(Float, nullable=False)
    """New Elo rating for away team."""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """Timestamp when the record was created."""

    __table_args__ = (
        Index("idx_elo_model_competition_season", "competition_id", "season"),
        Index("idx_elo_model_event_id", "event_id"),
    )
