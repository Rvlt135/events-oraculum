from datetime import datetime, UTC
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from sqlalchemy import Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.orm.base import Base


if TYPE_CHECKING:
    from app.infrastructure.db.orm.user import User


class IdentityProvider(str, Enum):
    GOOGLE = "google"
    PASSWORD = "password"
    TELEGRAM = "telegram"


class UserIdentity(Base):
    __tablename__ = "user_identities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[IdentityProvider] = mapped_column(
        SQLEnum(IdentityProvider, native_enum=False, length=20),
        nullable=False
    )
    provider_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_premium: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="identities")

    __table_args__ = (
        {"schema": None},
    )

