from datetime import datetime
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm.user_session import UserSession


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

