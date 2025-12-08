from uuid import UUID

from sqlalchemy import Integer, Index
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.orm.base import Base
from app.infrastructure.db.orm.mixins import TimestampMixin


class EventEdgeORM(Base, TimestampMixin):
    """Event edge model storing computed betting edges."""
    __tablename__ = "event_edges"

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
    )
    competition_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
    )
    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    edges_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_event_edges_competition_season", "competition_id", "season"),
    )