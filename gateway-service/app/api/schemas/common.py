"""
Common API schemas.
"""

from pydantic import BaseModel, Field


class InviteSettingUpdate(BaseModel):
    """Schema for Invite Code setting."""
    invite_code_required: bool = Field(..., description="Whether invite code is required for registration")
