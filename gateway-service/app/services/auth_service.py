from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

import structlog
from fastapi import Request, status
from fastapi.responses import RedirectResponse
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cache.redis import redis_cache_manager
from app.infrastructure.clients.google_oauth import google_oauth_client
from app.infrastructure.clients.telegram_validator import ParsedTelegramUser, TelegramValidator
from app.infrastructure.db.orm.user import PlanType, User
from app.infrastructure.db.orm.user_identity import IdentityProvider
from app.infrastructure.db.repositories.identity_repo import IdentityRepository
from app.infrastructure.db.repositories.session_repo import SessionRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.security.jwt import jwt_service
from app.infrastructure.security.password import PasswordService
from app.infrastructure.security.utils import generate_oauth_params
from app.services.cookies import set_auth_cookies
from app.services.exceptions import AuthorizationError
from app.services.google_oauth_validator import google_oauth_validator

logger = structlog.get_logger()


class BaseAuthService:
    jwt = jwt_service
    redis = redis_cache_manager

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session
        self.user_repo = UserRepository(db_session)
        self.identity_repo = IdentityRepository(db_session)
        self.session_repo = SessionRepository(db_session)

    async def logout(self, refresh_token: str) -> None:
        token_payload = self.jwt.verify_token(refresh_token, expected_type="refresh")
        jti = UUID(token_payload.jti)

        await self.session_repo.delete_by_jti(jti)
        await self._invalidate_session(jti)
        await self.db.commit()


    async def _cache_user(self, user: User) -> None:
        key = f"user:{user.id}"
        data = {
            "id": str(user.id),
            "email": user.email,
            "email_verified": user.email_verified,
            "plan_type": user.plan_type.value,
            "trial_end_at": user.trial_end_at.isoformat() if user.trial_end_at else None,
            "created_at": user.created_at.isoformat(),
        }
        await self.redis.set(key, data, ttl=300)

    async def _get_cached_user(self, user_id: UUID) -> User | None:
        key = f"user:{user_id}"
        data = await self.redis.get(key)
        if not data:
            return None
        return None

    async def _cache_session(self, jti: UUID, user_id: UUID, expires_at: datetime) -> None:
        key = f"session:{jti}"
        data = {
            "user_id": str(user_id),
            "expires_at": expires_at.isoformat(),
        }
        ttl = int((expires_at - datetime.now(UTC)).total_seconds())
        if ttl > 0:
            await self.redis.set(key, data, ttl=ttl)

    async def _get_cached_session(self, jti: UUID) -> dict | None:
        key = f"session:{jti}"
        data = await self.redis.get(key)
        if not data:
            return None
        return data

    async def _invalidate_session(self, jti: UUID) -> None:
        key = f"session:{jti}"
        await self.redis.delete(key)

    async def _cache_user_with_account_id(self, user: User, account_id: int) -> None:
        await self._cache_user(user)

        account_key = f"account:{account_id}"
        data = {
            "user_id": str(user.id),
        }
        await self.redis.set(account_key, data, ttl=300)

    async def _invalidate_user_cache(self, user_id: UUID, account_id: int | None = None) -> None:
        key = f"user:{user_id}"
        await self.redis.delete(key)

        if account_id:
            account_key = f"account:{account_id}"
            await self.redis.delete(account_key)


class GoogleAuthService(BaseAuthService):

    def __init__(self, db_session: AsyncSession, redirect_uri: str) -> None:
        super().__init__(db_session)
        self.google = google_oauth_client
        self.redirect_uri = redirect_uri

    async def login_with_google(
        self, code: str, state: str,
        ) -> str:
        try:
            cached_oauth_params = await self.get_cached_oauth_transaction(state)
            code_verifier = cached_oauth_params.get("code_verifier")
            token_data = await self.get_google_token(code, code_verifier)
            cached_nonce = cached_oauth_params.get("nonce")
            user_info = self.get_user_data_from_token(token_data=token_data, nonce=cached_nonce)
            self.verify_user_info(user_info)
        except AuthorizationError as e:
            redirect_url = f"/login?{urlencode({"error":e})}"
            return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)

        email = user_info.get("email")
        google_user_id = user_info.get("sub")
        email_verified = user_info.get("email_verified", False)

        identity = await self.identity_repo.get_by_provider(
            IdentityProvider.GOOGLE, google_user_id,
        )
        if identity:
            user = identity.user

        else:
            user = await self.user_repo.get_by_email(email)
            if not user:
                trial_end = datetime.now(UTC) + timedelta(days=7)
                user = await self.user_repo.create(
                    email=email,
                    email_verified=email_verified,
                    plan_type=PlanType.FREE,
                    trial_end_at=trial_end,
                )
            await self.identity_repo.create(
                user_id=user.id,
                provider=IdentityProvider.GOOGLE,
                provider_user_id=google_user_id,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"),
                photo_url=user_info.get("picture"),
            )

        access_token = self.jwt.create_access_token(user.id, user.plan_type.value)
        refresh_token, jti = self.jwt.create_refresh_token(user.id)

        refresh_expires = datetime.now(UTC) + timedelta(
            seconds=self.jwt.refresh_ttl,
        )
        await self.session_repo.create(
            jti=jti,
            user_id=user.id, 
            expires_at=refresh_expires,
            user_agent=cached_oauth_params.get("ua"),
        )

        await self._cache_session(jti, user.id, refresh_expires)
        await self.db.commit()
        response = RedirectResponse(url=cached_oauth_params.get("return_to"))

        set_auth_cookies(response, access_token, refresh_token)

        await self._delete_cached_transaction(state)

        return response

    async def get_google_token(self, code: str, code_verifier: str) -> dict:
        try:
            return await self.google.exchange_code(code, code_verifier)
        except (RuntimeError, HTTPStatusError):
            raise AuthorizationError("token_exchange_failed")
    
    def get_user_data_from_token(self, token_data: dict, nonce: str) -> dict:
        try:
            id_token = token_data.get("id_token")
            return self.google.verify_id_token(id_token=id_token, cached_nonce=nonce)
        except ValueError:
            raise AuthorizationError("invalid_id_token")
    
    def verify_user_info(self, data: dict) -> None:
        email = data.get("email")

        if not email:
            raise AuthorizationError("email_required")
    
    async def _delete_cached_transaction(self, state: str) -> None:
        key = f"oauth:state:{state}"
        await self.redis.delete(key)
        
             
    async def get_authorization_url(self, request: Request, return_to: str | None = None) -> str:

        return_to = google_oauth_validator.validate_and_parse_return_path(return_to)

        oauth_params = generate_oauth_params()

        cached_params = {
            "provider": "GOOGLE",
            "nonce": oauth_params.get("nonce"),
            "code_verifier": oauth_params.get("code_verifier"),
            "state": oauth_params.get("state"),
            "return_to": return_to,
            "redirect_uri": self.redirect_uri,
            "ip": "<client_ip>", # TODO need to get client ip
            "ua": request.headers.get("user-agent"),
            "created_at": datetime.now(UTC).isoformat(),
            "status": "PENDING",
        }
        
        await self._cache_oauth_transaction(cached_params)

        return self.google.get_authorization_url(oauth_params)

    async def _cache_oauth_transaction(self, params: dict, ttl: int = 600) -> None:
        state = params.pop("state")
        state_key = f"oauth:state:{state}"
        await redis_cache_manager.set(state_key, params, ttl)
    
    async def get_cached_oauth_transaction(self, state: str) -> dict | None:
        if state is None:
            raise AuthorizationError("invalid_state")
        
        key = f"oauth:state:{state}"
        data = await self.redis.get(key)

        if not data:
            raise AuthorizationError("state_expired")
        if data["status"] != "PENDING":
            raise AuthorizationError("state_used")
        return data


class TokenService(BaseAuthService):

    async def refresh_access_token(self, refresh_token: str) -> str:
        token_payload = self.jwt.verify_token(refresh_token, expected_type="refresh")
        jti = UUID(token_payload.jti)
        user_id = UUID(token_payload.sub)

        cached = await self._get_cached_session(jti)
        if not cached:
            db_session = await self.session_repo.get_by_jti(jti)
            if not db_session or db_session.expires_at < datetime.now(UTC):
                raise ValueError("Invalid or expired session")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        account_id = user.telegram_account_id if user.telegram_account_id else None
        return self.jwt.create_access_token(user.id, user.plan_type.value, account_id=account_id)


    async def get_user_by_id(self, user_id: UUID, use_cache: bool = True) -> User | None:
        if use_cache:
            cached = await self._get_cached_user(user_id)
            if cached:
                return cached

        user = await self.user_repo.get_by_id(user_id)
        if user and use_cache:
            await self._cache_user(user)
        return user


# TO DO refactor this service - split to separate services for each auth type
class AuthService(BaseAuthService):
    # def __init__(
    #     self,
    #     db_session: AsyncSession,
    #     # redis: RedisCache,
    #     # jwt_service: JWTService,
    password: PasswordService
    telegram: TelegramValidator
    # ):
    #     self.db = db_session
    #     self.password = password_service
    #     self.telegram = telegram_validator
    #     self.user_repo = UserRepository(db_session)
    #     self.identity_repo = IdentityRepository(db_session)
    #     self.session_repo = SessionRepository(db_session)

    async def register_with_email(
        self, email: str, password: str, user_agent: str | None = None
    ) -> tuple[User, str, str]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        password_hash = self.password.hash_password(password)
        trial_end = datetime.now(UTC) + timedelta(days=7)

        user = await self.user_repo.create(
            email=email,
            password_hash=password_hash,
            email_verified=False,
            plan_type=PlanType.FREE,
            trial_end_at=trial_end,
        )

        await self.identity_repo.create(
            user_id=user.id,
            provider=IdentityProvider.PASSWORD,
            provider_user_id=email,
        )

        access_token = self.jwt.create_access_token(user.id, user.plan_type.value)
        refresh_token, jti = self.jwt.create_refresh_token(user.id)

        refresh_expires = datetime.now(UTC) + timedelta(
            seconds=self.jwt.refresh_ttl
        )
        await self.session_repo.create(
            jti=jti, user_id=user.id, expires_at=refresh_expires, user_agent=user_agent
        )

        await self._cache_session(jti, user.id, refresh_expires)
        await self.db.commit()

        return user, access_token, refresh_token

    async def login_with_email(
        self, email: str, password: str, user_agent: str | None = None
    ) -> tuple[User, str, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not user.password_hash:
            raise ValueError("Invalid credentials")

        if not self.password.verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        access_token = self.jwt.create_access_token(user.id, user.plan_type.value)
        refresh_token, jti = self.jwt.create_refresh_token(user.id)

        refresh_expires = datetime.now(UTC) + timedelta(
            seconds=self.jwt.refresh_ttl
        )
        await self.session_repo.create(
            jti=jti, user_id=user.id, expires_at=refresh_expires, user_agent=user_agent
        )

        await self._cache_session(jti, user.id, refresh_expires)
        await self.db.commit()

        return user, access_token, refresh_token

    async def login_with_telegram(
        self, init_data_str: str, user_agent: str | None = None
    ) -> tuple[User, str, str]:
        if not self.telegram:
            raise ValueError("Telegram authentication not configured")

        parsed_user = self.telegram.validate_and_parse(init_data_str)
        account_id = parsed_user.account_id

        identity = await self.identity_repo.get_by_provider(
            IdentityProvider.TELEGRAM, str(account_id)
        )

        if identity:
            user = identity.user
            if user.telegram_account_id != account_id:
                user.telegram_account_id = account_id
                user.telegram_is_premium = parsed_user.is_premium
                await self.user_repo.update(user)
        else:
            user = await self.user_repo.get_by_telegram_account_id(account_id)

            if user:
                await self.identity_repo.create(
                    user_id=user.id,
                    provider=IdentityProvider.TELEGRAM,
                    provider_user_id=str(account_id),
                    username=parsed_user.username,
                    first_name=parsed_user.first_name,
                    last_name=parsed_user.last_name,
                    language_code=parsed_user.language_code,
                    photo_url=parsed_user.photo_url,
                    is_premium=parsed_user.is_premium,
                )
            else:
                trial_end = datetime.now(UTC) + timedelta(days=7)
                user = await self.user_repo.create(
                    email=None,
                    email_verified=False,
                    plan_type=PlanType.FREE,
                    trial_end_at=trial_end,
                    telegram_account_id=account_id,
                    telegram_is_premium=parsed_user.is_premium,
                )

                await self.identity_repo.create(
                    user_id=user.id,
                    provider=IdentityProvider.TELEGRAM,
                    provider_user_id=str(account_id),
                    username=parsed_user.username,
                    first_name=parsed_user.first_name,
                    last_name=parsed_user.last_name,
                    language_code=parsed_user.language_code,
                    photo_url=parsed_user.photo_url,
                    is_premium=parsed_user.is_premium,
                )

        access_token = self.jwt.create_access_token(
            user.id, user.plan_type.value, account_id=account_id
        )
        refresh_token, jti = self.jwt.create_refresh_token(user.id)

        refresh_expires = datetime.now(UTC) + timedelta(seconds=self.jwt.refresh_ttl)
        await self.session_repo.create(
            jti=jti, user_id=user.id, expires_at=refresh_expires, user_agent=user_agent
        )

        await self._cache_session(jti, user.id, refresh_expires)
        await self._cache_user_with_account_id(user, account_id)
        await self.db.commit()

        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> str:
        token_payload = self.jwt.verify_token(refresh_token, expected_type="refresh")
        jti = UUID(token_payload.jti)
        user_id = UUID(token_payload.sub)

        cached = await self._get_cached_session(jti)
        if not cached:
            db_session = await self.session_repo.get_by_jti(jti)
            if not db_session or db_session.expires_at < datetime.now(UTC):
                raise ValueError("Invalid or expired session")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        account_id = user.telegram_account_id if user.telegram_account_id else None
        return self.jwt.create_access_token(user.id, user.plan_type.value, account_id=account_id)

    async def get_user_by_id(self, user_id: UUID, use_cache: bool = True) -> User | None:
        if use_cache:
            cached = await self._get_cached_user(user_id)
            if cached:
                return cached

        user = await self.user_repo.get_by_id(user_id)
        if user and use_cache:
            await self._cache_user(user)
        return user
