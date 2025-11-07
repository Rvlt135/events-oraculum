from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.orm.user import User, PlanType
from app.infrastructure.db.orm.user_identity import IdentityProvider


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

    async def get_by_telegram_account_id(self, account_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.telegram_account_id == account_id)
            .options(selectinload(User.identities))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str | None = None,
        plan_type: PlanType = PlanType.FREE,
        password_hash: str | None = None,
        email_verified: bool = False,
        trial_end_at: datetime | None = None,
        telegram_account_id: int | None = None,
        telegram_is_premium: bool | None = None,
    ) -> User:
        user = User(
            email=email,
            email_verified=email_verified,
            password_hash=password_hash,
            telegram_account_id=telegram_account_id,
            telegram_is_premium=telegram_is_premium,
            plan_type=plan_type,
            trial_end_at=trial_end_at,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        from datetime import UTC
        user.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(user)
        return user

