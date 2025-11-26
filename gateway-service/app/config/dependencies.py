from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram_validator import TelegramValidator
from app.db.pg import get_session
from app.cache.redis import get_redis_cache
from app.config.settings import settings as _settings, Settings
from app.auth.service import JWTService, AuthService, GoogleOAuthService, PasswordService
from app.config.settings import settings
# get_telegram_validator moved here to avoid circular import


def get_settings() -> Settings:
    return _settings

def get_jwt_service() -> JWTService:
    return JWTService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl=settings.access_token_ttl_seconds,
        refresh_ttl=settings.refresh_token_ttl_seconds,
    )

def get_google_oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
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

async def get_auth_service(
    db: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis_cache),
    jwt_service: JWTService = Depends(get_jwt_service),
    password_service: PasswordService = Depends(get_password_service),
    google_oauth: GoogleOAuthService = Depends(get_google_oauth_service),
    telegram_validator: TelegramValidator | None = Depends(get_telegram_validator),
) -> AuthService:
    return AuthService(db, redis, jwt_service, password_service, google_oauth, telegram_validator)

