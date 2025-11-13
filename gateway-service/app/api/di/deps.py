from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, settings
from app.infrastructure.clients.telegram_validator import TelegramValidator
from app.infrastructure.db.session import get_session
from app.infrastructure.security.jwt import JWTService
from app.infrastructure.security.password import PasswordService
from app.services.auth_service import AuthService, GoogleAuthService, TokenService


def get_settings() -> Settings:
    return settings

def get_redis_client(request: Request) -> redis.Redis:
    client = getattr(request.app.state, "redis_client", None)
    if client is None:
        raise RuntimeError("Redis client not initialized")
    return client

def get_redis_cache(request: Request) -> RedisCache:
    cache = getattr(request.app.state, "redis_cache", None)
    if cache is None:
        raise RuntimeError("Redis cache not initialized")
    return cache


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

# TODO - remove/update this method with the refactoring AuthService 
async def get_auth_service(
    db: AsyncSession = Depends(get_session),
) -> AuthService:
    return AuthService(db_session=db)
