from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Text, Numeric, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.db.orm.base import Base


class EventPriority(Base):
    __tablename__ = "event_priorities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider = Column(Text, nullable=False)
    provider_key = Column(Text, nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    priority = Column(Numeric(4, 3), nullable=False)
    model = Column(Text, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta = Column(JSONB, nullable=True, default=dict)

    event = relationship("Event", back_populates="priorities")

    __table_args__ = (
        UniqueConstraint("provider_key", "event_id", name="uq_event_priorities_provider_key_event_id"),
        Index("idx_event_priorities_provider_key_priority", "provider_key", "priority", postgresql_ops={"priority": "DESC"}),
        Index("idx_event_priorities_event_id", "event_id"),
        Index("idx_event_priorities_evaluated_at", "evaluated_at"),
    )

