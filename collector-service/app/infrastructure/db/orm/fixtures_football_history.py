from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, SmallInteger, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.infrastructure.db.orm.base import Base


class FixturesFootballHistory(Base):
    """History of finished fixtures for Elo algo."""
    __tablename__ = "fixtures_football_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    api_fixture_id = Column(Integer, nullable=False, unique=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    season = Column(Integer, nullable=False)
    match_date = Column(DateTime(timezone=True), nullable=False)
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    result = Column(SmallInteger, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_fixtures_football_history_competition_season", "competition_id", "season"),
        Index("idx_fixtures_football_history_match_date", "match_date"),
        UniqueConstraint("api_fixture_id", name="uq_fixtures_football_history_api_fixture_id"),
    )