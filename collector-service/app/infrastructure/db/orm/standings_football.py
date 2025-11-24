from uuid import uuid4
from typing import Optional
from sqlalchemy import Column, DateTime, ForeignKey, Text, Integer, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base

class StandingsFootball(Base):
    __tablename__ = "standings_football"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=True)
    points = Column(Integer, nullable=True)
    goal_diff = Column(Integer, nullable=True)
    all_played = Column(Integer, nullable=True)
    all_win = Column(Integer, nullable=True)
    all_draw = Column(Integer, nullable=True)
    all_lose = Column(Integer, nullable=True)
    all_goals_for = Column(Integer, nullable=True)
    all_goals_against = Column(Integer, nullable=True)
    home_played = Column(Integer, nullable=True)
    home_win = Column(Integer, nullable=True)
    home_draw = Column(Integer, nullable=True)
    home_lose = Column(Integer, nullable=True)
    home_goals_for = Column(Integer, nullable=True)
    home_goals_against = Column(Integer, nullable=True)
    away_played = Column(Integer, nullable=True)
    away_win = Column(Integer, nullable=True)
    away_draw = Column(Integer, nullable=True)
    away_lose = Column(Integer, nullable=True)
    away_goals_for = Column(Integer, nullable=True)
    away_goals_against = Column(Integer, nullable=True)
    form_raw = Column(Text, nullable=True)
    status = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    team = relationship("Team")
    competition = relationship("Competition")

    __table_args__ = (
        UniqueConstraint("team_id", "competition_id", "season", name="uq_standings_football_team_competition_season"),
        Index("idx_standings_football_team_id", "team_id"),
        Index("idx_standings_football_competition_id", "competition_id"),
    )

