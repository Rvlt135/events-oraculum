from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncpg
import structlog

logger = structlog.get_logger()


class PostgresClient:
    def __init__(self, postgres_url: str) -> None:
        self.postgres_url = postgres_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.postgres_url.replace("postgresql+asyncpg://", "postgresql://"),
                min_size=2,
                max_size=10,
            )
            logger.info("postgres_connected")

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("postgres_disconnected")

    async def fetch_one(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args: Any) -> List[asyncpg.Record]:
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def get_or_create_sport(self, name: str, display_name: str) -> UUID:
        query = """
            INSERT INTO sports (name, display_name, is_active)
            VALUES ($1, $2, true)
            ON CONFLICT (name) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
        """
        result = await self.fetch_one(query, name, display_name)
        return result["id"]

    async def get_or_create_league(
        self, sport_id: UUID, key: str, name: str, region: str
    ) -> UUID:
        query = """
            INSERT INTO leagues (sport_id, key, name, region, is_active)
            VALUES ($1, $2, $3, $4, true)
            ON CONFLICT (key) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """
        result = await self.fetch_one(query, sport_id, key, name, region)
        return result["id"]

    async def get_or_create_team(
        self, name: str, normalized_name: str, sport_id: UUID, external_ids: Dict[str, Any]
    ) -> UUID:
        query = """
            INSERT INTO teams (name, normalized_name, sport_id, external_ids)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (normalized_name) DO UPDATE
            SET name = EXCLUDED.name, external_ids = EXCLUDED.external_ids, updated_at = now()
            RETURNING id
        """
        result = await self.fetch_one(query, name, normalized_name, sport_id, external_ids)
        return result["id"]

    async def get_or_create_bookmaker(self, key: str, name: str, region: str) -> UUID:
        query = """
            INSERT INTO bookmakers (key, name, region, is_active)
            VALUES ($1, $2, $3, true)
            ON CONFLICT (key) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """
        result = await self.fetch_one(query, key, name, region)
        return result["id"]

    async def create_or_update_event(
        self,
        external_id: str,
        sport_id: UUID,
        league_id: UUID,
        home_team_id: UUID,
        away_team_id: UUID,
        commence_time: datetime,
        status: str,
        metadata: Dict[str, Any],
    ) -> UUID:
        query = """
            INSERT INTO events (
                external_id, sport_id, league_id, home_team_id, away_team_id,
                commence_time, status, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (external_id) DO UPDATE SET
                commence_time = EXCLUDED.commence_time,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata,
                updated_at = now()
            RETURNING id
        """
        result = await self.fetch_one(
            query,
            external_id,
            sport_id,
            league_id,
            home_team_id,
            away_team_id,
            commence_time,
            status,
            metadata,
        )
        return result["id"]

    async def create_odds_snapshot(
        self,
        event_id: UUID,
        bookmaker_id: UUID,
        market_type: str,
        outcomes: Dict[str, Any],
        timestamp_source: datetime,
    ) -> UUID:
        query = """
            INSERT INTO odds_snapshots (
                event_id, bookmaker_id, market_type, outcomes, timestamp_source, timestamp_ingested
            )
            VALUES ($1, $2, $3, $4, $5, now())
            RETURNING id
        """
        result = await self.fetch_one(
            query, event_id, bookmaker_id, market_type, outcomes, timestamp_source
        )
        return result["id"]

    async def create_normalized_odds(
        self,
        event_id: UUID,
        market_type: str,
        home_odds_avg: float,
        away_odds_avg: float,
        draw_odds_avg: Optional[float],
        home_odds_best: float,
        away_odds_best: float,
        draw_odds_best: Optional[float],
        bookmakers_count: int,
        timestamp_source: datetime,
        timestamp_ingested: datetime,
    ) -> UUID:
        query = """
            INSERT INTO normalized_odds (
                event_id, market_type, home_odds_avg, away_odds_avg, draw_odds_avg,
                home_odds_best, away_odds_best, draw_odds_best, bookmakers_count,
                timestamp_source, timestamp_ingested
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
        """
        result = await self.fetch_one(
            query,
            event_id,
            market_type,
            home_odds_avg,
            away_odds_avg,
            draw_odds_avg,
            home_odds_best,
            away_odds_best,
            draw_odds_best,
            bookmakers_count,
            timestamp_source,
            timestamp_ingested,
        )
        return result["id"]

    async def get_normalized_snapshots(
        self, limit: int = 100, league_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if league_key:
            query = """
                SELECT
                    n.*,
                    e.external_id,
                    l.key as league_key,
                    t1.name as home_team,
                    t2.name as away_team,
                    e.commence_time
                FROM normalized_odds n
                JOIN events e ON n.event_id = e.id
                JOIN leagues l ON e.league_id = l.id
                JOIN teams t1 ON e.home_team_id = t1.id
                JOIN teams t2 ON e.away_team_id = t2.id
                WHERE l.key = $1
                ORDER BY n.timestamp_normalized DESC
                LIMIT $2
            """
            rows = await self.fetch_all(query, league_key, limit)
        else:
            query = """
                SELECT
                    n.*,
                    e.external_id,
                    l.key as league_key,
                    t1.name as home_team,
                    t2.name as away_team,
                    e.commence_time
                FROM normalized_odds n
                JOIN events e ON n.event_id = e.id
                JOIN leagues l ON e.league_id = l.id
                JOIN teams t1 ON e.home_team_id = t1.id
                JOIN teams t2 ON e.away_team_id = t2.id
                ORDER BY n.timestamp_normalized DESC
                LIMIT $1
            """
            rows = await self.fetch_all(query, limit)
        return [dict(row) for row in rows]
