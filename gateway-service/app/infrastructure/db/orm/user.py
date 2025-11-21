from datetime import datetime, UTC
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, DateTime, BigInteger, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.orm.base import Base


if TYPE_CHECKING:
    from app.infrastructure.db.orm.user_identity import UserIdentity
    from app.infrastructure.db.orm.user_session import UserSession
    from app.infrastructure.db.orm.invite_code import InviteCode


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    PARTNER = "partner"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_type: Mapped[PlanType] = mapped_column(
        SQLEnum(PlanType, native_enum=False, length=20),
        default=PlanType.FREE,
        nullable=False
    )
    trial_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_account_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True)
    telegram_is_premium: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )
    ref_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    refferer_code: Mapped[str | None] = mapped_column(String(8), nullable=True)

    identities: Mapped[list["UserIdentity"]] = relationship("UserIdentity", back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    invite_codes: Mapped["InviteCode"] = relationship("InviteCode", back_populates="User", cascade="all, delete-orphan")
