from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header

from app.auth.jwt_utils import JWTService
from app.auth.password_utils import PasswordService
from app.auth.google_oauth import GoogleOAuthService
from app.auth.telegram_validator import TelegramValidator

from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.config.settings import settings
from app.db.pg import get_session
from app.cache.redis import get_redis_cache
from app.auth.service import AuthService
from app.config.dependencies import get_auth_service, get_google_oauth_service, get_jwt_service, get_telegram_validator

async def get_current_user(
    authorization: str | None = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
    jwt_service: JWTService = Depends(get_jwt_service),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt_service.verify_token(token, expected_type="access")
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