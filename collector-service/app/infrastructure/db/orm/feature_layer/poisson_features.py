from uuid import uuid4
from sqlalchemy import Column, ForeignKey, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.db.orm.base import Base
from app.infrastructure.db.orm.mixins import TimestampMixin


class PoissonFeatures(Base, TimestampMixin):
    """Poisson features model for feature layer."""
    __tablename__ = "poisson_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    """Primary key identifier."""
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    """Reference to the event."""
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    """Reference to the home team."""
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    """Reference to the away team."""
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    """Reference to the competition."""
    season = Column(Integer, nullable=False)
    """Season year."""
    lambda_home = Column(Float)
    """Lambda parameter for home team."""
    lambda_away = Column(Float)
    """Lambda parameter for away team."""
    home_strength = Column(Float)
    """Home team strength."""
    away_strength = Column(Float)
    """Away team strength."""
    expected_goals_home = Column(Float)
    """Expected goals for home team."""
    expected_goals_away = Column(Float)
    """Expected goals for away team."""

    __table_args__ = (
        Index("idx_poisson_features_competition_season", "competition_id", "season"),
        UniqueConstraint("event_id", name="uq_poisson_features_event_id"),
    )
