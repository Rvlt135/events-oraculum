from uuid import uuid4
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Integer, Numeric, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base



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
