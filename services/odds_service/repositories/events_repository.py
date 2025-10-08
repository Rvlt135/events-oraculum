from datetime import datetime
from typing import Any
from uuid import UUID

from services.odds_service.repositories.base import BaseRepository


class EventsRepository(BaseRepository):
    async def get_or_create_sport(self, name: str, display_name: str) -> UUID:
        query = """
            INSERT INTO sports (name, display_name, is_active)
            VALUES ($1, $2, true)
            ON CONFLICT (name) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
        """
        result = await self.fetch_one(query, name, display_name)
        return result["id"] if result else None

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
        return result["id"] if result else None

    async def get_or_create_team(
        self, name: str, normalized_name: str, sport_id: UUID, external_ids: dict[str, Any]
    ) -> UUID:
        query = """
            INSERT INTO teams (name, normalized_name, sport_id, external_ids)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (normalized_name) DO UPDATE
            SET name = EXCLUDED.name, external_ids = EXCLUDED.external_ids, updated_at = now()
            RETURNING id
        """
        result = await self.fetch_one(query, name, normalized_name, sport_id, external_ids)
        return result["id"] if result else None

    async def get_or_create_bookmaker(self, key: str, name: str, region: str) -> UUID:
        query = """
            INSERT INTO bookmakers (key, name, region, is_active)
            VALUES ($1, $2, $3, true)
            ON CONFLICT (key) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """
        result = await self.fetch_one(query, key, name, region)
        return result["id"] if result else None

    async def create_or_update_event(
        self,
        external_id: str,
        sport_id: UUID,
        league_id: UUID,
        home_team_id: UUID,
        away_team_id: UUID,
        commence_time: datetime,
        status: str,
        metadata: dict[str, Any],
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
        return result["id"] if result else None

    async def create_odds_snapshot(
        self,
        event_id: UUID,
        bookmaker_id: UUID,
        market_type: str,
        outcomes: dict[str, Any],
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
        return result["id"] if result else None

    async def create_normalized_odds(
        self,
        event_id: UUID,
        market_type: str,
        home_odds_avg: float,
        away_odds_avg: float,
        draw_odds_avg: float | None,
        home_odds_best: float,
        away_odds_best: float,
        draw_odds_best: float | None,
        bookmakers_count: int,
    ) -> UUID:
        query = """
            INSERT INTO normalized_odds (
                event_id, market_type, home_odds_avg, away_odds_avg, draw_odds_avg,
                home_odds_best, away_odds_best, draw_odds_best, bookmakers_count
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
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
        )
        return result["id"] if result else None

    async def get_upcoming_events(self, league_id: UUID) -> list[dict[str, Any]]:
        query = """
            SELECT e.*, t1.name as home_team_name, t2.name as away_team_name
            FROM events e
            JOIN teams t1 ON e.home_team_id = t1.id
            JOIN teams t2 ON e.away_team_id = t2.id
            WHERE e.league_id = $1 AND e.status = 'upcoming'
            ORDER BY e.commence_time
        """
        rows = await self.fetch_all(query, league_id)
        return [dict(row) for row in rows]
