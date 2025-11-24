from uuid import uuid4
from typing import Optional
from sqlalchemy import Column, DateTime, ForeignKey, Text, Integer, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.infrastructure.db.orm.base import Base

class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    team_slug = Column(Text, nullable=False)
    sport_id = Column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="CASCADE"), nullable=False)
    external_ids = Column(JSONB, default=dict)
    external_apif_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sport = relationship("Sport", back_populates="teams")

    __table_args__ = (
        UniqueConstraint("sport_id", "normalized_name", name="uq_teams_sport_normalized_name"),
        UniqueConstraint("sport_id", "team_slug", name="uq_teams_sport_team_slug"),
        Index("idx_teams_sport_id", "sport_id"),
        Index("idx_teams_sport_normalized_name", "sport_id", "normalized_name"),
        Index("idx_teams_sport_team_slug", "sport_id", "team_slug"),
        Index("idx_teams_external_apif_id", "external_apif_id"),
    )
