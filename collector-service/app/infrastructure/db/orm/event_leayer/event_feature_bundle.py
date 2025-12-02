from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.orm.base import Base


class EventFeatureBundleORM(Base):
    """Event feature bundle model storing enriched event features."""
    __tablename__ = "event_feature_bundles"

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
    )
    competition_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        index=True,
        nullable=False,
    )
    season: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )
    bundle_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )