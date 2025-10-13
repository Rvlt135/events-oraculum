from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Numeric, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base
from app.domain.time_utils import now_utc, now_utc_func


class Sport(Base):
    __tablename__ = "sports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, unique=True, nullable=False)
    display_name = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    leagues = relationship("League", back_populates="sport")
    teams = relationship("Team", back_populates="sport")
    events = relationship("Event", back_populates="sport")


class League(Base):
    __tablename__ = "leagues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sport_id = Column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="CASCADE"), nullable=False)
    key = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    region = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sport = relationship("Sport", back_populates="leagues")
    events = relationship("Event", back_populates="league")

    __table_args__ = (
        Index("idx_leagues_sport_id", "sport_id"),
        Index("idx_leagues_is_active", "is_active"),
    )


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, unique=True, nullable=False)
    sport_id = Column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="CASCADE"), nullable=False)
    external_ids = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sport = relationship("Sport", back_populates="teams")

    __table_args__ = (
        Index("idx_teams_sport_id", "sport_id"),
        Index("idx_teams_normalized_name", "normalized_name"),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(Text, unique=True, nullable=False)
    sport_id = Column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="CASCADE"), nullable=False)
    league_id = Column(UUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    commence_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Text, default="upcoming")
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sport = relationship("Sport", back_populates="events")
    league = relationship("League", back_populates="events")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    odds_snapshots = relationship("OddsSnapshot", back_populates="event")
    normalized_odds = relationship("NormalizedOdds", back_populates="event")

    __table_args__ = (
        Index("idx_events_sport_id", "sport_id"),
        Index("idx_events_league_id", "league_id"),
        Index("idx_events_commence_time", "commence_time"),
        Index("idx_events_status", "status"),
        Index("idx_events_external_id", "external_id"),
    )


class Bookmaker(Base):
    __tablename__ = "bookmakers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    region = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    odds_snapshots = relationship("OddsSnapshot", back_populates="bookmaker")

    __table_args__ = (
        Index("idx_bookmakers_key", "key"),
        Index("idx_bookmakers_is_active", "is_active"),
    )


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    bookmaker_id = Column(UUID(as_uuid=True), ForeignKey("bookmakers.id", ondelete="CASCADE"), nullable=False)
    market_type = Column(Text, nullable=False)
    outcomes = Column(JSONB, nullable=False)
    timestamp_source = Column(DateTime(timezone=True), nullable=False)
    timestamp_ingested = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("Event", back_populates="odds_snapshots")
    bookmaker = relationship("Bookmaker", back_populates="odds_snapshots")

    __table_args__ = (
        Index("idx_odds_snapshots_event_id", "event_id"),
        Index("idx_odds_snapshots_bookmaker_id", "bookmaker_id"),
        Index("idx_odds_snapshots_market_type", "market_type"),
        Index("idx_odds_snapshots_timestamp_ingested", "timestamp_ingested", postgresql_ops={"timestamp_ingested": "DESC"}),
    )


class NormalizedOdds(Base):
    __tablename__ = "normalized_odds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    market_type = Column(Text, nullable=False)
    home_odds_avg = Column(Numeric(10, 2), nullable=False)
    away_odds_avg = Column(Numeric(10, 2), nullable=False)
    draw_odds_avg = Column(Numeric(10, 2), nullable=True)
    home_odds_best = Column(Numeric(10, 2), nullable=False)
    away_odds_best = Column(Numeric(10, 2), nullable=False)
    draw_odds_best = Column(Numeric(10, 2), nullable=True)
    bookmakers_count = Column(Integer, nullable=False, default=0)
    timestamp_source = Column(DateTime(timezone=True), nullable=False)
    timestamp_ingested = Column(DateTime(timezone=True), nullable=False)
    timestamp_normalized = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("Event", back_populates="normalized_odds")

    __table_args__ = (
        Index("idx_normalized_odds_event_id", "event_id"),
        Index("idx_normalized_odds_market_type", "market_type"),
        Index("idx_normalized_odds_timestamp_normalized", "timestamp_normalized", postgresql_ops={"timestamp_normalized": "DESC"}),
    )
