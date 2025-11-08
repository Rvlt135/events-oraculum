from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.clients.telegram_validator import TelegramValidator
from app.infrastructure.db.session import get_session
from app.infrastructure.cache.redis import get_redis_cache, RedisCache
from app.config.settings import settings, Settings
from app.infrastructure.security.jwt import JWTService
from app.infrastructure.security.password import PasswordService
from app.infrastructure.clients.google_oauth import GoogleOAuthClient
from app.services.auth_service import AuthService, GoogleAuthService, TokenService

def get_settings() -> Settings:
    return settings


def get_jwt_service() -> JWTService:
    return JWTService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl=settings.access_token_ttl_seconds,
        refresh_ttl=settings.refresh_token_ttl_seconds,
    )


def get_password_service() -> PasswordService:
    return PasswordService()


def get_telegram_validator() -> TelegramValidator | None:
    if not settings.telegram_bot_token:
        return None
    return TelegramValidator(
        bot_token=settings.telegram_bot_token,
        max_auth_age_seconds=settings.telegram_max_auth_age_seconds,
    )


async def get_google_auth_service(
    db: AsyncSession = Depends(get_session),
) -> GoogleAuthService:
    return GoogleAuthService(db_session=db, redirect_uri=settings.google_redirect_uri)


async def get_token_service(
    db: AsyncSession = Depends(get_session),
) -> TokenService:
    return TokenService(db_session=db)

# TO DO - remove this method with the refactoring AuthService 
async def get_auth_service(
    db: AsyncSession = Depends(get_session),
    redis: RedisCache = Depends(get_redis_cache),
    jwt_service: JWTService = Depends(get_jwt_service),
    password_service: PasswordService = Depends(get_password_service),
    telegram_validator: TelegramValidator | None = Depends(get_telegram_validator),
) -> AuthService:
    return AuthService(db, redis, jwt_service, password_service, telegram_validator)