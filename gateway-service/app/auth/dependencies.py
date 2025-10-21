from typing import Literal
from fastapi import HTTPException, status, Depends
from app.domain.auth_models import User, PlanType
from app.routes.auth import get_current_user


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
