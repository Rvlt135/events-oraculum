from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, settings
from app.infrastructure.cache.oauth_cache import OauthCache
from app.infrastructure.cache.redis import RedisCache
from app.infrastructure.cache.session_cache import SessionCache
from app.infrastructure.cache.user_cache import UserCache
from app.infrastructure.clients.telegram_validator import TelegramValidator
from app.infrastructure.db.session import get_session
from app.infrastructure.security.password import PasswordService
from app.services.auth_service import EmailAuthService, GoogleAuthService, TokenService


def get_settings() -> Settings:
    return settings


def get_redis_client(request: Request) -> Redis:
    client = getattr(request.app.state, "redis_client", None)
    if client is None:
        raise RuntimeError("Redis client not initialized")
    return client


def get_redis_cache(request: Request) -> RedisCache:
    cache = getattr(request.app.state, "redis_cache", None)
    if cache is None:
        raise RuntimeError("Redis cache not initialized")
    return cache


def get_session_cache(redis_client: RedisCache = Depends(get_redis_cache)) -> SessionCache:
    return SessionCache(redis=redis_client)


def get_oauth_cache(redis_client: RedisCache = Depends(get_redis_cache)) -> OauthCache:
    return OauthCache(redis=redis_client)


def get_user_cache(redis_client: RedisCache = Depends(get_redis_cache)) -> UserCache:
    return UserCache(redis=redis_client)


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
    session_cache: SessionCache = Depends(get_session_cache),
    oauth_cache: OauthCache = Depends(get_oauth_cache),
) -> GoogleAuthService:
    return GoogleAuthService(
        db_session=db,
        session_cache=session_cache,
        oauth_cache=oauth_cache,
    )


async def get_token_service(
    db: AsyncSession = Depends(get_session),
    session_cache: SessionCache = Depends(get_session_cache),
    user_cache: UserCache =  Depends(get_user_cache)
) -> TokenService:
    return TokenService(db_session=db, session_cache=session_cache, user_cache=user_cache)


async def get_email_auth_service(
    db: AsyncSession = Depends(get_session),
    user_cache: UserCache =  Depends(get_user_cache),
    session_cashe: SessionCache = Depends(get_session_cache),
) -> EmailAuthService:
    return EmailAuthService(db_session=db, user_cache=user_cache, session_cache=session_cashe)
