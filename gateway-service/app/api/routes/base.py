from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from app.api.di.auth_deps import get_current_user
from app.api.schemas.user import (
    MeResponse,
    UserProfile,
)
from app.infrastructure.db.orm.user import User

router = APIRouter()


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
) -> MeResponse:
    trial_left_days = None
    is_trial_active = False

    if user.trial_end_at:
        delta = user.trial_end_at - datetime.now(UTC)
        trial_left_days = max(0, delta.days)
        is_trial_active = delta.total_seconds() > 0
    resp = MeResponse(
        user=UserProfile.model_validate(user),
        trial_left_days=trial_left_days,
        is_trial_active=is_trial_active,
    )
    return resp.model_dump(exclude_none=True) # TODO: убрать null в будущем в ответе


# Dummy endpoints for development

@router.get("/dashboard")
def get_dashboard(
    user: User = Depends(get_current_user)
) -> dict:
    print(user)
    return {"user": str(user)}


@router.get("/login")
def login(error: str | None = Query(...)) -> dict:
    return {
        "endpoint": "/login",
        "query": error,
    }
