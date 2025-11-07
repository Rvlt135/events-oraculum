from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.auth import AuthTokens


class TelegramInfo(BaseModel):
    """Schema for Telegram user information."""
    account_id: int = Field(..., description="Telegram account ID")
    username: str | None = Field(None, description="Telegram username")
    first_name: str | None = Field(None, description="First name from Telegram")
    last_name: str | None = Field(None, description="Last name from Telegram")
    language_code: str | None = Field(None, description="Language code from Telegram")
    photo_url: str | None = Field(None, description="Profile photo URL from Telegram")
    is_premium: bool = Field(False, description="Whether user has Telegram Premium")

    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    id: UUID
    email: str
    email_verified: bool
    plan_type: str
    trial_end_at: datetime | None
    created_at: datetime
    telegram: TelegramInfo | None = Field(None, description="Telegram user information")

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    user: UserProfile
    tokens: AuthTokens


class MeResponse(BaseModel):
    user: UserProfile
    trial_left_days: int | None
    is_trial_active: bool

