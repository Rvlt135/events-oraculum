from uuid import uuid4
from sqlalchemy import Column, ForeignKey, Integer, Float, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.db.orm.base import Base


class MatchFeatures(Base):
    """Match features model for feature layer."""
    __tablename__ = "match_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    """Primary key identifier."""
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    """Reference to the team."""
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    """Reference to the competition."""
    season = Column(Integer, nullable=False)
    """Season year."""
    last_matches_count = Column(Integer)
    """Number of last matches considered."""
    goals_for_last_n = Column(Integer)
    """Goals scored in last N matches."""
    goals_against_last_n = Column(Integer)
    """Goals conceded in last N matches."""
    goals_diff_last_n = Column(Integer)
    """Goal difference in last N matches."""
    wins_last_n = Column(Integer)
    """Wins in last N matches."""
    draws_last_n = Column(Integer)
    """Draws in last N matches."""
    losses_last_n = Column(Integer)
    """Losses in last N matches."""
    avg_goals_for_last_n = Column(Float)
    """Average goals scored in last N matches."""
    avg_goals_against_last_n = Column(Float)
    """Average goals conceded in last N matches."""
    form_last_n = Column(Text)
    """Form string for last N matches."""

    __table_args__ = (
        Index("idx_match_features_team", "team_id"),
        Index("idx_match_features_comp_season", "competition_id", "season"),
        UniqueConstraint("team_id", "competition_id", "season", name="uq_match_features_team_competition_season"),
    )