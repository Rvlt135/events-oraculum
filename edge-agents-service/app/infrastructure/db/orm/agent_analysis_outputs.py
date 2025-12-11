from uuid import UUID
from typing import Dict, Any

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.orm.base import Base
from app.infrastructure.db.orm.mixins import TimestampMixin


class AgentAnalysisOutputsORM(Base, TimestampMixin):
    """ORM model storing agent analysis outputs for events."""
    
    __tablename__ = "agent_analysis_outputs"
    
    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("events.id"),
        primary_key=True,
    )
    
    outputs_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    main_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    
    decision: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return f"<AgentAnalysisOutputsORM(event_id={self.event_id}, main_score={self.main_score})>"