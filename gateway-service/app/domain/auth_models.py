from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    PARTNER = "partner"


class IdentityProvider(str, Enum):
    GOOGLE = "google"
    PASSWORD = "password"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_type: Mapped[PlanType] = mapped_column(
        SQLEnum(PlanType, native_enum=False, length=20),
        default=PlanType.FREE,
        nullable=False
    )
    trial_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    identities: Mapped[list["UserIdentity"]] = relationship("UserIdentity", back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserIdentity(Base):
    __tablename__ = "user_identities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[IdentityProvider] = mapped_column(
        SQLEnum(IdentityProvider, native_enum=False, length=20),
        nullable=False
    )
    provider_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="identities")

    __table_args__ = (
        {"schema": None},
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    jti: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")
