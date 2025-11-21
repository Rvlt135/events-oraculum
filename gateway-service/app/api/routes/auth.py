import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.api.di.deps import get_auth_service, get_google_auth_service
from app.api.schemas.auth import (
    EmailLoginRequest,
    EmailRegisterRequest,
    TelegramAuthRequest,
    TokenRefreshRequest,
)
from app.api.schemas.user import (
    AuthResponse,
    AuthTokens,
    TelegramInfo,
    UserProfile,
)
from app.services.auth_service import (
    EmailAuthService,
    GoogleAuthService,
    TelegramAuthService,
    TokenService,
)
from app.services.exceptions import ValidationError

router = APIRouter(prefix="/auth", tags=["auth"])

logger = structlog.get_logger()


@router.get("/google/start")
async def google_oauth_start(
    request: Request,
    return_to: str | None = Query(None, description="Конечный маршрут после логина"),
    auth_service: GoogleAuthService = Depends(get_google_auth_service)
) -> RedirectResponse:
    
    try:
        auth_url = await auth_service.get_authorization_url(
            request=request, return_path=return_to)
        
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    
    except ValidationError as e:
        logger.error("invalid_return_to", value=return_to)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.name,
                "message": e.message,
            },
        )
    
    except Exception as e:
        logger.error("Unable to initialize OAuth flow:", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "OAuth_start_failed",
                "message": "Unable to initialize OAuth flow",
            },
        )
    

@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(),
    state: str = Query(),
    auth_service: GoogleAuthService = Depends(get_google_auth_service),
) -> RedirectResponse:
    try:
        return await auth_service.login_with_google(code, state)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth failed: {e!s}",
        )


@router.post("/register")
async def register_with_email(
    reg_data: EmailRegisterRequest,
    request: Request,
    return_to: str | None = Query(None, description="Конечный маршрут после логина"),
    auth_service: EmailAuthService = Depends(get_auth_service),
) -> RedirectResponse:
    try:
        return await auth_service.register_with_email(
            reg_data, request, return_to)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {e!s}",
        )


@router.post("/email/login", response_model=AuthResponse)
async def login_with_email(
    req: EmailLoginRequest,
    request: Request,
    auth_service: EmailAuthService = Depends(get_auth_service),
):
    try:
        user_agent = request.headers.get("user-agent")
        user, access_token, refresh_token = await auth_service.login_with_email(
            req.email, req.password, user_agent)

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
    auth_service: TokenService = Depends(get_auth_service),
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
    auth_service: TelegramAuthService = Depends(get_auth_service),
):
    try:
        user_agent = request.headers.get("user-agent")
        # Extract init_data from payload
        from app.api.schemas.auth import TelegramAuthData
        if isinstance(req.payload, TelegramAuthData):
            init_data = req.payload.init_data
        else:
            # Fallback for WebAppAuthData
            init_data = getattr(req.payload, "payload", "") or getattr(req.payload, "init_data", "")
        
        if not init_data:
            raise ValueError("init_data not found in payload")
            
        user, access_token, refresh_token = await auth_service.login_with_telegram(
            init_data, user_agent
        )

        telegram_info = None
        if user.identities:
            from app.infrastructure.db.orm.user_identity import IdentityProvider
            telegram_identity = next(
                (i for i in user.identities if i.provider == IdentityProvider.TELEGRAM),
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
    auth_service: EmailAuthService = Depends(get_auth_service),
):
    try:
        await auth_service.logout(req.refresh_token)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
