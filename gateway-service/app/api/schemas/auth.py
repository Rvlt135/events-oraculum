from datetime import datetime
from enum import Enum
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class AuthType(str, Enum):
    TELEGRAM = "TELEGRAM"
    WEBAPP = "WEBAPP"


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TelegramAuthData(BaseModel):
    """Schema for Telegram WebApp authentication data."""
    init_data: str = Field(..., description="Telegram WebApp initData string")

    model_config = ConfigDict(
        extra="ignore"
    )


class WebAppAuthData(BaseModel):
    """
    Schema for WebApp authentication data using Telegram initData.
    This is used for web-based Telegram authentication.
    """
    type: AuthType = Field(..., description="Authentication type")
    referral_token: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Optional referrer ID for tracking"
    )
    payload: str = Field(..., description="Telegram WebApp initData string")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore"
    )


class TelegramAuthRequest(BaseModel):
    """Base schema for authentication requests."""
    type: AuthType = Field(..., description="Authentication type")
    payload: Union[TelegramAuthData, WebAppAuthData] = Field(
        ...,
        description="Authentication data specific to the auth type"
    )
    referral_token: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Optional referrer ID for tracking"
    )
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra='ignore'
    )


class TelegramUserData(BaseModel):
    """Schema for creating user from Telegram data."""
    user_id: str = Field(..., description="Generated UUID for user")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="First name from Telegram")
    last_name: Optional[str] = Field(None, description="Last name from Telegram")
    telegram_id: str = Field(..., description="Telegram user ID")
    telegram_username: Optional[str] = Field(None, description="Telegram username")
    photo_url: Optional[str] = Field(None, description="Profile photo URL")
    is_active: bool = Field(True, description="User active status")
    email: Optional[str] = Field(None, description="Email address")

    model_config = ConfigDict(from_attributes=True)

