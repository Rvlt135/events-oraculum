from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.api.di.deps import get_auth_service, get_token_service
from app.config.settings import settings
from app.infrastructure.db.orm.user import User
from app.infrastructure.security.jwt import jwt_service
from app.services.auth_service import TokenService

security = HTTPBearer(scheme_name="Bearer")

async def get_current_user(
    request: Request,
    auth_service: TokenService = Depends(get_token_service),
) -> User:
    access_token = request.cookies.get(settings.access_token_cookie_name)
    try:
        payload = jwt_service.verify_token(access_token, expected_type="access")
        user_id = UUID(payload.sub)
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


# TODO: actualize
def require_plan(min_plan: Literal["free", "pro", "partner"] = "free"):
    async def _check_plan(user: User = Depends(get_current_user)):
        plan_hierarchy = {
            "free": 0,
            "pro": 1,
            "partner": 2,
        }

        user_level = plan_hierarchy.get(user.plan_type.value, 0)
        required_level = plan_hierarchy.get(min_plan, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {min_plan} plan or higher",
            )

        return user

    return _check_plan

