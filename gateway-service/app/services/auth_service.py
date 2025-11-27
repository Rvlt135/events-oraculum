from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import EmailLoginRequest, EmailRegisterRequest
from app.infrastructure.cache.oauth_cache import OauthCache
from app.infrastructure.cache.session_cache import SessionCache
from app.infrastructure.cache.settings_cache import SettingCache
from app.infrastructure.cache.user_cache import UserCache
from app.infrastructure.clients.google_oauth import google_oauth_client
from app.infrastructure.clients.telegram_validator import telegram_validator
from app.infrastructure.db.orm.invite_code import InviteCode
from app.infrastructure.db.orm.user import PlanType, User
from app.infrastructure.db.orm.user_identity import IdentityProvider
from app.infrastructure.db.repositories.identity_repo import IdentityRepository
from app.infrastructure.db.repositories.invite_code_repo import InviteCodeRepository
from app.infrastructure.db.repositories.session_repo import SessionRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.security.jwt import jwt_service
from app.infrastructure.security.password import password_service
from app.infrastructure.security.utils import generate_oauth_params
from app.services.cookies import clear_auth_cookies, get_auth_cookies, set_auth_cookies
from app.services.email_auth_validator import email_auth_validator
from app.services.exceptions import AuthorizationError
from app.services.google_oauth_validator import google_oauth_validator

logger = structlog.get_logger()


class BaseAuthService:
    jwt = jwt_service

    def __init__(self, db_session: AsyncSession, session_cache: SessionCache) -> None:
        self.db = db_session
        self.user_repo = UserRepository(db_session)
        self.identity_repo = IdentityRepository(db_session)
        self.session_repo = SessionRepository(db_session)
        self.session_cache = session_cache
    
    async def _create_and_cache_session(
        self, jti: UUID, user_id: UUID, user_agent: str) -> None:

        refresh_expires = datetime.now(UTC) + timedelta(
            seconds=self.jwt.refresh_ttl,
        )
        await self.session_repo.create(
            jti=jti,
            user_id=user_id, 
            expires_at=refresh_expires,
            user_agent=user_agent,
        )
        await self.session_cache.cache_session(jti, user_id, refresh_expires)


class GoogleAuthService(BaseAuthService):
    validator = google_oauth_validator

    def __init__(
            self,
            db_session: AsyncSession,
            session_cache: SessionCache,
            oauth_cache: OauthCache,
    ) -> None:
        super().__init__(db_session, session_cache)
        self.google = google_oauth_client
        self.oauth_cache = oauth_cache

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
            logger.info(
                "Google OAuth authorization failed.",
                state=state,
                error=str(e),
            )
            redirect_url = f"/login?{urlencode({"error":e})}"
            return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)

        email = user_info.get("email").lower()
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

        logger.info(
            "User registered in with Google OAuth.",
            state=state,
            user_id=str(user.id),
            email=user.email,
            google_user_id=google_user_id,
            retuturn_to=cached_oauth_params.get("return_to"),
        )

        access_token, refresh_token, jti = self.jwt.create_tokens_for_user(
            user.id, user.plan_type.value)

        await self._create_and_cache_session(jti, user.id, cached_oauth_params.get("ua"))

        await self.db.commit()

        response = RedirectResponse(url=cached_oauth_params.get("return_to"))
        set_auth_cookies(response, access_token, refresh_token)

        await self.oauth_cache.invalidate_transation(state)

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
    
    async def get_authorization_url(self, request: Request, return_path: str | None = None) -> str:

        return_path = self.validator.validate_and_parse_return_path(return_path)

        oauth_params = generate_oauth_params()

        logger.info(
            "Start Google authorization.",
            state=oauth_params.get("state"),
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent"), 
            x_request_id=request.headers.get("X-Request-ID", None),
        )

        request_params = {
            "return_to": return_path,
            "ip": request.client.host,
            "ua": request.headers.get("user-agent"),
        }
        
        await self.oauth_cache.cache_oauth_transaction(oauth_params, request_params)

        return self.google.get_authorization_url(oauth_params)

    async def get_cached_oauth_transaction(self, state: str) -> dict | None:
        if state is None:
            raise AuthorizationError("invalid_state")
        data = await self.oauth_cache.get_cached_oauth_transation(state)

        if not data:
            raise AuthorizationError("state_expired")
        if data["status"] != "PENDING":
            raise AuthorizationError("state_used")
        return data


class TokenService(BaseAuthService):

    def __init__(
        self,
        db_session: AsyncSession,
        session_cache: SessionCache,
        user_cache: UserCache,
    ) -> None:
        super().__init__(db_session, session_cache)
        self.user_cache = user_cache

    async def refresh_access_token(self, request: Request) -> RedirectResponse:
        _, refresh_token = get_auth_cookies(request).values()
        token_payload = self.jwt.verify_token(refresh_token, expected_type="refresh")
        jti = UUID(token_payload.jti)
        user_id = UUID(token_payload.sub)

        cached = await self.session_cache.get_cached_session(jti)
        if not cached:
            db_session = await self.session_repo.get_by_jti(jti)
            if not db_session or db_session.expires_at < datetime.now(UTC):
                raise ValueError("Invalid or expired session")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        access_token = self.jwt.create_access_token(user.id, user.plan_type.value)
        response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
        set_auth_cookies(response, access_token, refresh_token)
        return response

    async def get_user_by_id(self, user_id: UUID, use_cache: bool = True) -> User | None:
        if use_cache:
            cached = await self.user_cache.get_cached_user(user_id)
            if cached:
                return cached

        user = await self.user_repo.get_by_id(user_id)
        if user and use_cache:
            await self.user_cache.cache_user(user)
        return user
    
    async def logout(self, request: Request) -> RedirectResponse:
        _, refresh_token = get_auth_cookies(request).values()
        token_payload = self.jwt.verify_token(refresh_token, expected_type="refresh")
        jti = UUID(token_payload.jti)

        await self.session_repo.delete_by_jti(jti)
        await self.session_cache.invalidate_session(jti)
        await self.db.commit()
        # TODO: redirect to return_to if provided or return JSON response
        response = RedirectResponse(url="/login")
        clear_auth_cookies(response)
        return response


class EmailAuthService(BaseAuthService):
    password = password_service
    validator = email_auth_validator

    def __init__(
        self,
        db_session: AsyncSession,
        user_cache: UserCache,
        session_cache: SessionCache,
        settings_cache: SettingCache,
    ) -> None:
        super().__init__(db_session, session_cache)
        self.user_cache = user_cache
        self.invite_code_repo = InviteCodeRepository(db_session)
        self.settings_cache = settings_cache

    async def register_with_email(
        self, reg_data: EmailRegisterRequest, request: Request, return_to: str,
    ) -> RedirectResponse:
        try:
            return_path = self.validator.validate_and_parse_return_path(return_to)
            self.validator.validate_password(reg_data.password)

            require_invite = await self.settings_cache.get_setting_cache(
                key="invite_code_required") == "true"
            code = await self.validate_invite_code(reg_data.invite_code) if require_invite else None

            referrer = await self.validate_referral_code(reg_data.referral_code) if reg_data.referral_code else None
            email = reg_data.email.lower()
            await self.validate_email_not_taken(email)
        except AuthorizationError as e:
            logger.info(
                "User registration with email failed.",
                email=reg_data.email,
                invite_code=reg_data.invite_code,
                referral_code=reg_data.referral_code,
                error=str(e),
            )            
            redirect_url = f"/login?{urlencode({"error":e})}"
            return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)

        user_agent = request.headers.get("ua")

        password_hash = self.password.hash_password(reg_data.password)
        trial_end = datetime.now(UTC) + timedelta(days=7)
        user = await self.user_repo.create(
            email=email,
            password_hash=password_hash,
            email_verified=False,
            plan_type=PlanType.FREE,
            trial_end_at=trial_end,
            referrer_code=reg_data.referral_code if referrer else None,
        )
        if code:
            await self.invite_code_repo.mark_used(code, user.id)
        await self.identity_repo.create(
            user_id=user.id,
            provider=IdentityProvider.PASSWORD,
            provider_user_id=email,
        )
        logger.info(
            "User registered with email.",
            user_id=str(user.id),
            email=user.email,
            invite_code=reg_data.invite_code,
            referral_code=reg_data.referral_code[:4] + "..." if reg_data.referral_code else None,
        )

        access_token, refresh_token, jti = self.jwt.create_tokens_for_user(
            user.id, user.plan_type.value)

        await self._create_and_cache_session(jti, user.id, user_agent)

        await self.db.commit()

        response = RedirectResponse(url=return_path)
        set_auth_cookies(response, access_token, refresh_token)

        return response
    
    async def validate_invite_code(self, code_str: str) -> InviteCode:
        self.validator.validate_invite_code(code_str)
        code = await self.invite_code_repo.get_by_code(code_str)
        if not code:
            raise AuthorizationError("invite_invalid")
        if code.user_id is not None or code.registration_date is not None:
            raise AuthorizationError("invite_used")
        return code
    
    async def validate_referral_code(self, ref_code: str) -> User | None:
        referrer = await self.user_repo.get_by_ref_code(ref_code)
        if not referrer:
            raise AuthorizationError("referrer_invalid")
        return referrer
    
    async def validate_email_not_taken(self, email: str) -> None:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise AuthorizationError("email_taken")

    async def login_with_email(
        self, data: EmailLoginRequest, reqest: Request, return_to: str,
    ) -> RedirectResponse:
        try:
            return_path = self.validator.validate_and_parse_return_path(return_to)
            user = await self.get_user(data.email.lower(), data.password)
        except AuthorizationError as e:
            logger.info(
                "User login with email failed.",
                email=data.email,
                error=str(e),
            )            
            redirect_url = f"/login?{urlencode({'error':e})}"
            return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)
        
        user_agent = reqest.headers.get("user-agent")

        access_token, refresh_token, jti = self.jwt.create_tokens_for_user(
            user.id, user.plan_type.value)

        await self._create_and_cache_session(jti, user.id, user_agent)

        await self.db.commit()

        logger.info(
            "User logged in with email.",
            user_id=str(user.id),
            email=user.email,
            retuturn_to=return_path,
        )

        response = RedirectResponse(url=return_path)
        set_auth_cookies(response, access_token, refresh_token)

        return response
    
    async def get_user(self, email: str, password: str) -> User | None:
        user = await self.user_repo.get_by_email(email)
        if not user or not user.password_hash:
            raise AuthorizationError("Invalid credentials")

        if not self.password.verify_password(password, user.password_hash):
            raise AuthorizationError("Invalid credentials")

        return user


# TODO refactor this service
class TelegramAuthService:
    password = password_service
    telegram = telegram_validator

    def __init__(self, db_session: AsyncSession, user_cache: UserCache):
        self.user_cache = user_cache
        self.user_repo = UserRepository(db_session)

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
            cached = await self.user_cache.get_cached_user(user_id)
            if cached:
                return cached

        user = await self.user_repo.get_by_id(user_id)
        if user and use_cache:
            await self.user_cache.cache_user(user)
        return user
