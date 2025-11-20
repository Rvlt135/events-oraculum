from uuid import uuid4
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Text, Index, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base

class Competition(Base):
    __tablename__ = "competitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    sport_id = Column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="CASCADE"), nullable=False)

    title = Column(Text, nullable=False, comment='Напр.: UEFA Champions League или EPL')
    description = Column(Text, nullable=True, comment='Напр.: English Premier League, Опционально, из провайдера')
    provider = Column(Text, nullable=False, default='odds_api', comment='Источник данных, (mvp - odds_api)')
    slug_key = Column(Text, nullable=False, comment='Из sports.key, напр.: "soccer_uefa_champs_league"')
    plan_visibility = Column(Text, nullable=False, default="free")

    is_active = Column(Boolean, nullable=False, comment='payload.active из провайдера; без default, ставим явно в инжесте')

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment='При обновлении сompetition например is_active -> true или false')

    sport = relationship("Sport", back_populates="competitions")
    events = relationship("Event", back_populates="competition")

    __table_args__ = (
        UniqueConstraint("provider", "slug_key", name="uq_competitions_slug_key"),
        Index("idx_competitions_sport_id", "sport_id"),
        Index("idx_competitions_is_active", "is_active"),
    )
