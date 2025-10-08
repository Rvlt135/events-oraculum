import asyncpg
from shared.config import DatabaseConfig


class BaseRepository:
    def __init__(self, db_config: DatabaseConfig) -> None:
        self.db_config = db_config
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.db_config.postgres_url,
                min_size=2,
                max_size=10,
            )

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def fetch_one(self, query: str, *args: Any) -> asyncpg.Record | None:
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args: Any) -> list[asyncpg.Record]:
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)


from typing import Any
