from uuid import uuid4
from sqlalchemy import Column, ForeignKey, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.db.orm.base import Base
from app.infrastructure.db.orm.mixins import TimestampMixin


class TeamFeatures(Base, TimestampMixin):
    """Team features model for feature layer."""
    __tablename__ = "team_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    season = Column(Integer, nullable=False)
    strength_initial = Column(Float, nullable=False)
    form_score = Column(Float, nullable=False)
    goals_for_avg = Column(Float, nullable=False)
    goals_against_avg = Column(Float, nullable=False)
    goal_diff = Column(Integer, nullable=False)
    games_played = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_team_features_competition_season", "competition_id", "season"),
        UniqueConstraint("team_id", "competition_id", "season", name="uq_team_features_team_competition_season"),
    )