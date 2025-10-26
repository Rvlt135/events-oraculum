from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse

from app.auth.google_oauth import GoogleOAuthService
from app.auth.schemas import (
    EmailRegisterRequest,
    EmailLoginRequest,
    TelegramAuthRequest,
    AuthResponse,
    AuthTokens,
    UserProfile,
    TelegramInfo,
    TokenRefreshRequest,
    MeResponse,
)
from app.auth.service import AuthService
from app.security.authorization import get_auth_service, get_google_oauth_service, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.post("/telegram", response_model=AuthResponse)
async def login_with_telegram(
    req: TelegramAuthRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user_agent = request.headers.get("user-agent")
        user, access_token, refresh_token = await auth_service.login_with_telegram(
            req.init_data, user_agent
        )

        telegram_info = None
        if user.identities:
            telegram_identity = next(
                (i for i in user.identities if i.provider == "telegram"),
                None
            )
            if telegram_identity:
                telegram_info = TelegramInfo(
                    account_id=user.telegram_account_id,
                    username=telegram_identity.username,
                    first_name=telegram_identity.first_name,
                    last_name=telegram_identity.last_name,
                    language_code=telegram_identity.language_code,
                    photo_url=telegram_identity.photo_url,
                    is_premium=telegram_identity.is_premium or False,
                )

        user_profile = UserProfile.model_validate(user)
        user_profile.telegram = telegram_info

        return AuthResponse(
            user=user_profile,
            tokens=AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Telegram authentication failed: {str(e)}",
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
