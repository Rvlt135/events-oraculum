from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from app.api.di.auth_deps import get_current_user
from app.api.di.deps import get_settings_cache
from app.api.schemas.common import InviteSettingUpdate
from app.api.schemas.user import (
    MeResponse,
    UserProfile,
)
from app.infrastructure.cache.settings_cache import SettingCache
from app.infrastructure.db.orm.user import User
from app.infrastructure.db.repositories.invite_code_repo import InviteCodeRepository
from app.infrastructure.db.session import get_session

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


@router.put("/settings/invite_code_required")
async def update_invite_code_setting(
    req: InviteSettingUpdate,
    settings_cache: SettingCache = Depends(get_settings_cache),
    # TODO: add admin dependency
) -> dict:
    await settings_cache.set_setting_cache(
        key="invite_code_required",
        value="true" if req.invite_code_required else "false",
    )
    return {
        "message": "Invite code requirement updated",
        "invite_code_required": req.invite_code_required,
    }


@router.get("/settings/invite_code_required")
async def get_invite_code_setting(
    settings_cache: SettingCache = Depends(get_settings_cache),
    # TODO: add admin dependency
) -> InviteSettingUpdate:
    value = await settings_cache.get_setting_cache(
        key="invite_code_required",
    )
    invite_code_required = value.lower() == "true"
    return InviteSettingUpdate(
        invite_code_required=invite_code_required,
    )

# Dummy endpoints for development

@router.get("/dashboard")
def get_dashboard(
    user: User = Depends(get_current_user)
) -> dict:
    return {"user": str(user)}


@router.get("/login")
def login(error: str | None = Query(...)) -> dict:
    return {
        "endpoint": "/login",
        "query": error,
    }

# Endpoint to generate invite codes in DB for testing
@router.post("/create-invite-codes")
async def create_invite_code(
    session = Depends(get_session)
) -> dict:
    code_repo = InviteCodeRepository(session)
    new_code = await code_repo.add_code()
    await session.commit()
    return {
        "invite_code": f"{new_code.code}",
    }   