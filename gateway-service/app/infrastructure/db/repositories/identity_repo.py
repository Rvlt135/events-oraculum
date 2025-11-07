from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.orm.user_identity import UserIdentity, IdentityProvider


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
        self,
        user_id: UUID,
        provider: IdentityProvider,
        provider_user_id: str,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
        photo_url: str | None = None,
        is_premium: bool | None = None,
    ) -> UserIdentity:
        identity = UserIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            photo_url=photo_url,
            is_premium=is_premium,
        )
        self.session.add(identity)
        await self.session.flush()
        await self.session.refresh(identity)
        return identity

