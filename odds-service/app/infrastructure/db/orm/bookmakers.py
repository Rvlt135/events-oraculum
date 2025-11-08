from uuid import uuid4
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Integer, Numeric, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base

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
