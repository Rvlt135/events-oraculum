from datetime import datetime
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.domain.auth_models import User, UserIdentity, UserSession, IdentityProvider, PlanType


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.identities))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.identities))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        plan_type: PlanType = PlanType.FREE,
        password_hash: str | None = None,
        email_verified: bool = False,
        trial_end_at: datetime | None = None,
    ) -> User:
        user = User(
            email=email,
            email_verified=email_verified,
            password_hash=password_hash,
            plan_type=plan_type,
            trial_end_at=trial_end_at,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        user.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(user)
        return user


class IdentityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_provider(
        self, provider: IdentityProvider, provider_user_id: str
    ) -> UserIdentity | None:
        result = await self.session.execute(
            select(UserIdentity)
            .where(
                UserIdentity.provider == provider,
                UserIdentity.provider_user_id == provider_user_id,
            )
            .options(selectinload(UserIdentity.user))
        )
        return result.scalar_one_or_none()

    async def create(
        self, user_id: UUID, provider: IdentityProvider, provider_user_id: str
    ) -> UserIdentity:
        identity = UserIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        self.session.add(identity)
        await self.session.flush()
        await self.session.refresh(identity)
        return identity


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        jti: UUID,
        user_id: UUID,
        expires_at: datetime,
        user_agent: str | None = None,
    ) -> UserSession:
        session = UserSession(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
        )
        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)
        return session

    async def get_by_jti(self, jti: UUID) -> UserSession | None:
        result = await self.session.execute(
            select(UserSession).where(UserSession.jti == jti)
        )
        return result.scalar_one_or_none()

    async def delete_by_jti(self, jti: UUID) -> None:
        await self.session.execute(
            delete(UserSession).where(UserSession.jti == jti)
        )
        await self.session.flush()

    async def delete_expired(self, before: datetime) -> int:
        result = await self.session.execute(
            delete(UserSession).where(UserSession.expires_at < before)
        )
        await self.session.flush()
        return result.rowcount
