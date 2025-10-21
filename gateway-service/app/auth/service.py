from datetime import datetime, timedelta
from uuid import UUID
import orjson
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.jwt_utils import JWTService
from app.auth.password_utils import PasswordService
from app.auth.repositories import UserRepository, IdentityRepository, SessionRepository
from app.auth.google_oauth import GoogleOAuthService
from app.auth.telegram_validator import TelegramValidator, ParsedTelegramUser
from app.domain.auth_models import PlanType, IdentityProvider, User


class AuthService:
    def __init__(
        self,
        db_session: AsyncSession,
        redis: Redis,
        jwt_service: JWTService,
        password_service: PasswordService,
        google_oauth: GoogleOAuthService,
        telegram_validator: TelegramValidator | None = None,
    ):
        self.db = db_session
        self.redis = redis
        self.jwt = jwt_service
        self.password = password_service
        self.google = google_oauth
        self.telegram = telegram_validator
        self.user_repo = UserRepository(db_session)
        self.identity_repo = IdentityRepository(db_session)
        self.session_repo = SessionRepository(db_session)

    async def register_with_email(
        self, email: str, password: str, user_agent: str | None = None
    ) -> tuple[User, str, str]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        password_hash = self.password.hash_password(password)
        trial_end = datetime.utcnow() + timedelta(days=7)

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

        refresh_expires = datetime.utcnow() + timedelta(
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

        refresh_expires = datetime.utcnow() + timedelta(
            seconds=self.jwt.refresh_ttl
        )
        await self.session_repo.create(
            jti=jti, user_id=user.id, expires_at=refresh_expires, user_agent=user_agent
        )

        await self._cache_session(jti, user.id, refresh_expires)
        await self.db.commit()

        return user, access_token, refresh_token

    async def login_with_google(
        self, code: str, user_agent: str | None = None
    ) -> tuple[User, str, str]:
        token_data = await self.google.exchange_code(code)
        id_token = token_data.get("id_token")
        if not id_token:
            raise ValueError("No ID token received")

        user_info = self.google.verify_id_token(id_token)
        email = user_info.get("email")
        google_user_id = user_info.get("sub")
        email_verified = user_info.get("email_verified", False)

        if not email or not google_user_id:
            raise ValueError("Invalid user info from Google")

        identity = await self.identity_repo.get_by_provider(
            IdentityProvider.GOOGLE, google_user_id
        )

        if identity:
            user = identity.user
        else:
            user = await self.user_repo.get_by_email(email)
            if not user:
                trial_end = datetime.utcnow() + timedelta(days=7)
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
            )

        access_token = self.jwt.create_access_token(user.id, user.plan_type.value)
        refresh_token, jti = self.jwt.create_refresh_token(user.id)

        refresh_expires = datetime.utcnow() + timedelta(
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
                trial_end = datetime.utcnow() + timedelta(days=7)
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

        refresh_expires = datetime.utcnow() + timedelta(seconds=self.jwt.refresh_ttl)
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
            if not db_session or db_session.expires_at < datetime.utcnow():
                raise ValueError("Invalid or expired session")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        account_id = user.telegram_account_id if user.telegram_account_id else None
        return self.jwt.create_access_token(user.id, user.plan_type.value, account_id=account_id)

    async def logout(self, refresh_token: str) -> None:
        token_payload = self.jwt.verify_token(refresh_token, expected_type="refresh")
        jti = UUID(token_payload.jti)

        await self.session_repo.delete_by_jti(jti)
        await self._invalidate_session(jti)
        await self.db.commit()

    async def get_user_by_id(self, user_id: UUID, use_cache: bool = True) -> User | None:
        if use_cache:
            cached = await self._get_cached_user(user_id)
            if cached:
                return cached

        user = await self.user_repo.get_by_id(user_id)
        if user and use_cache:
            await self._cache_user(user)
        return user

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
        await self.redis.setex(key, 300, orjson.dumps(data))

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
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            await self.redis.setex(key, ttl, orjson.dumps(data))

    async def _get_cached_session(self, jti: UUID) -> dict | None:
        key = f"session:{jti}"
        data = await self.redis.get(key)
        if not data:
            return None
        return orjson.loads(data)

    async def _invalidate_session(self, jti: UUID) -> None:
        key = f"session:{jti}"
        await self.redis.delete(key)

    async def _cache_user_with_account_id(self, user: User, account_id: int) -> None:
        await self._cache_user(user)

        account_key = f"account:{account_id}"
        data = {
            "user_id": str(user.id),
        }
        await self.redis.setex(account_key, 300, orjson.dumps(data))

    async def _invalidate_user_cache(self, user_id: UUID, account_id: int | None = None) -> None:
        key = f"user:{user_id}"
        await self.redis.delete(key)

        if account_id:
            account_key = f"account:{account_id}"
            await self.redis.delete(account_key)
