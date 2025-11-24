from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.infrastructure.db.orm.invite_code import InviteCode

logger = structlog.get_logger()

class InviteCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def generate_code(self, length: int, alphabet: str) -> str:
        import random

        return ''.join(random.choice(alphabet) for _ in range(length))

    async def add_code(
        self,
    ) -> InviteCode:
        for _ in range(10):
            try:
                code = self.generate_code(
                    length=settings.invite_code_length,
                    alphabet=settings.invite_code_alphabet,
                )
                code_db = InviteCode(
                    code=code,
                )
                self.session.add(code_db)
                await self.session.flush()
                await self.session.refresh(code_db)

                return code_db
            except Exception:
                await self.session.rollback()
        logger.error("Failed to create invite code after multiple attempts due to collisions.")
        raise Exception("Failed to create invite code after multiple attempts due to collisions.")

    async def get_by_code(self, code: str) -> InviteCode | None:
        result = await self.session.execute(
            select(InviteCode).where(InviteCode.code == code).with_for_update(),
        )
        return result.scalar_one_or_none()

    async def mark_used(self, code: InviteCode, user_id: UUID) -> InviteCode:
        code.user_id = user_id
        code.registration_date = datetime.now(UTC)

        self.session.add(code)
        await self.session.flush()
        await self.session.refresh(code)
        return code
     