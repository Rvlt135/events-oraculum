from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm.invite_code import InviteCode


class InviteCodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        code: str,
    ) -> InviteCode:
        # TODO implement adding codes to DB
        code_db = InviteCode(
            code=code,
        )
        self.session.add(code_db)
        await self.session.flush()
        await self.session.refresh(code_db)
        return code_db

    async def get_by_code(self, code: str) -> InviteCode | None:
        result = await self.session.execute(
            select(InviteCode).where(InviteCode.code == code),
        )
        return result.scalar_one_or_none()

    async def use_code(self, code: InviteCode, user_id: UUID) -> InviteCode:
        code.user_id = user_id
        code.registration_date = datetime.now(UTC)

        self.session.add(code)
        await self.session.flush()
        await self.session.refresh(code)
        return code
     