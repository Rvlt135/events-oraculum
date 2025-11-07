from uuid import uuid4
from sqlalchemy import Column, Boolean, DateTime, Text, Index, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base

class Sport(Base):
    __tablename__ = "sports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider = Column(Text, nullable=False, default='odds_api', comment='Источник данных, mvp - odds_api')
    category = Column(Text, nullable=False, comment=', напр. soccer, tennis, basketball, ice hockey')
    is_active = Column(Boolean, nullable=False, comment='Выставляется явно инжестом (зеркало факта наличия активных competitions)')
    available = Column(Boolean, nullable=False, comment='')

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    competitions = relationship("Competition", back_populates="sport", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="sport", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="sport", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("provider", "category", name="uq_sports_provider_category"),
        Index("idx_sports_is_active", "is_active"),
    )