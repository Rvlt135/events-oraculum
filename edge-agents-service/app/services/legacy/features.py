from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
import asyncpg
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings

logger = structlog.get_logger()


class FeatureBuilder:
    def __init__(self, postgres_url: str):
        self.postgres_url = postgres_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.postgres_url.replace("postgresql+asyncpg://", "postgresql://"),
                min_size=2,
                max_size=10,
            )
            logger.info("feature_builder_connected")

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("feature_builder_disconnected")

    async def get_event_features(self, event_id: UUID) -> Optional[Dict[str, Any]]:
        if not self.pool:
            await self.connect()

        query = """
            SELECT
                e.external_id,
                e.commence_time,
                l.key as league_key,
                l.name as league_name,
                t1.name as home_team,
                t2.name as away_team,
                n.home_odds_avg,
                n.away_odds_avg,
                n.draw_odds_avg,
                n.home_odds_best,
                n.away_odds_best,
                n.draw_odds_best,
                n.bookmakers_count,
                n.timestamp_source,
                n.timestamp_ingested
            FROM events e
            JOIN leagues l ON e.league_id = l.id
            JOIN teams t1 ON e.home_team_id = t1.id
            JOIN teams t2 ON e.away_team_id = t2.id
            LEFT JOIN normalized_odds n ON e.id = n.event_id AND n.market_type = 'h2h'
            WHERE e.id = $1
            ORDER BY n.created_at DESC
            LIMIT 1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, event_id)

            if not row:
                logger.warning("event_not_found", event_id=str(event_id))
                return None

            features = dict(row)
            logger.info("features_built", event_id=str(event_id), home=features["home_team"])

            return features

    async def get_events_by_league(
        self, league_key: str, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> List[UUID]:
        if not self.pool:
            await self.connect()

        query = """
            SELECT e.id
            FROM events e
            JOIN leagues l ON e.league_id = l.id
            WHERE l.key = $1
        """

        params: List[Any] = [league_key]

        if from_date:
            query += " AND e.commence_time >= $2"
            params.append(from_date)

        if to_date:
            idx = len(params) + 1
            query += f" AND e.commence_time <= ${idx}"
            params.append(to_date)

        query += " AND e.status = 'upcoming' ORDER BY e.commence_time"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [row["id"] for row in rows]


class FeatureService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_event_features(self, event_id: UUID) -> Optional[Dict[str, Any]]:
        query = text("""
            SELECT
                e.external_id,
                e.commence_time,
                l.key as league_key,
                l.name as league_name,
                t1.name as home_team,
                t2.name as away_team,
                n.home_odds_avg,
                n.away_odds_avg,
                n.draw_odds_avg,
                n.home_odds_best,
                n.away_odds_best,
                n.draw_odds_best,
                n.bookmakers_count,
                n.timestamp_source,
                n.timestamp_ingested
            FROM events e
            JOIN leagues l ON e.league_id = l.id
            JOIN teams t1 ON e.home_team_id = t1.id
            JOIN teams t2 ON e.away_team_id = t2.id
            LEFT JOIN normalized_odds n ON e.id = n.event_id AND n.market_type = 'h2h'
            WHERE e.id = :event_id
            ORDER BY n.created_at DESC
            LIMIT 1
        """)
        async with self.session_factory() as session:
            result = await session.execute(query, {"event_id": event_id})
            row = result.fetchone()

            if not row:
                logger.warning("event_not_found", event_id=str(event_id))
                return None

            features = dict(row._mapping)
            logger.info("features_built", event_id=str(event_id), home=features.get("home_team"))

            return features
