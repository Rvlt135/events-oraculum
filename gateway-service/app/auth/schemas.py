from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


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


class UserProfile(BaseModel):
    id: UUID
    email: str
    email_verified: bool
    plan_type: str
    trial_end_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserProfile
    tokens: AuthTokens


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    user: UserProfile
    trial_left_days: int | None
    is_trial_active: bool
