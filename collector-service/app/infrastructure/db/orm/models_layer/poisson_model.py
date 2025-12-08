from sqlalchemy import Column, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.infrastructure.db.orm.base import Base
from app.infrastructure.db.orm.mixins import TimestampMixin


class PoissonModel(Base, TimestampMixin):
    """Poisson model predictions for events."""
    __tablename__ = "poisson_model"

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    """Primary key and reference to the event."""
    competition_id = Column(UUID(as_uuid=True), nullable=False)
    """Reference to the competition."""
    season = Column(Integer, nullable=False)
    """Season year."""
    p_home = Column(Float, nullable=False)
    """Probability of home team win."""
    p_draw = Column(Float, nullable=False)
    """Probability of draw."""
    p_away = Column(Float, nullable=False)
    """Probability of away team win."""
    fair_home = Column(Float, nullable=False)
    """Fair odds for home team."""
    fair_draw = Column(Float, nullable=False)
    """Fair odds for draw."""
    fair_away = Column(Float, nullable=False)
    """Fair odds for away team."""
    goal_probs_home = Column(JSONB, nullable=False)
    """Goal probabilities for home team (P(0..6))."""
    goal_probs_away = Column(JSONB, nullable=False)
    """Goal probabilities for away team (P(0..6))."""

    __table_args__ = (
        Index("idx_poisson_model_competition_season", "competition_id", "season"),
        Index("idx_poisson_model_event_id", "event_id"),
    )