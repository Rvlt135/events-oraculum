from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.auth.service import AuthService
from app.auth.jwt_utils import JWTService
from app.auth.password_utils import PasswordService
from app.auth.google_oauth import GoogleOAuthService
from app.auth.schemas import (
    EmailRegisterRequest,
    EmailLoginRequest,
    AuthResponse,
    AuthTokens,
    UserProfile,
    TokenRefreshRequest,
    MeResponse,
)
from app.config.dependencies import get_db_session, get_redis
from app.config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def get_jwt_service() -> JWTService:
    return JWTService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl=settings.access_token_ttl_seconds,
        refresh_ttl=settings.refresh_token_ttl_seconds,
    )


def get_password_service() -> PasswordService:
    return PasswordService()


def get_google_oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )


async def get_auth_service(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    jwt_service: JWTService = Depends(get_jwt_service),
    password_service: PasswordService = Depends(get_password_service),
    google_oauth: GoogleOAuthService = Depends(get_google_oauth_service),
) -> AuthService:
    return AuthService(db, redis, jwt_service, password_service, google_oauth)


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


@router.get("/google/start")
async def google_oauth_start(
    google_oauth: GoogleOAuthService = Depends(get_google_oauth_service),
):
    auth_url = google_oauth.get_authorization_url()
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user_agent = request.headers.get("user-agent")
        user, access_token, refresh_token = await auth_service.login_with_google(
            code, user_agent
        )

        return AuthResponse(
            user=UserProfile.model_validate(user),
            tokens=AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth failed: {str(e)}",
        )


@router.post("/email/register", response_model=AuthResponse)
async def register_with_email(
    req: EmailRegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user_agent = request.headers.get("user-agent")
        user, access_token, refresh_token = await auth_service.register_with_email(
            req.email, req.password, user_agent
        )

        return AuthResponse(
            user=UserProfile.model_validate(user),
            tokens=AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if "already" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/email/login", response_model=AuthResponse)
async def login_with_email(
    req: EmailLoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user_agent = request.headers.get("user-agent")
        user, access_token, refresh_token = await auth_service.login_with_email(
            req.email, req.password, user_agent
        )

        return AuthResponse(
            user=UserProfile.model_validate(user),
            tokens=AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )


@router.post("/token/refresh")
async def refresh_token(
    req: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        access_token = await auth_service.refresh_access_token(req.refresh_token)
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout")
async def logout(
    req: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        await auth_service.logout(req.refresh_token)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/me", response_model=MeResponse)
async def get_me(
    user = Depends(get_current_user),
):
    trial_left_days = None
    is_trial_active = False

    if user.trial_end_at:
        delta = user.trial_end_at - datetime.utcnow()
        trial_left_days = max(0, delta.days)
        is_trial_active = delta.total_seconds() > 0

    return MeResponse(
        user=UserProfile.model_validate(user),
        trial_left_days=trial_left_days,
        is_trial_active=is_trial_active,
    )
