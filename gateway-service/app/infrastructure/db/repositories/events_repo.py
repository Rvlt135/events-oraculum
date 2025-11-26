from typing import Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()


class EventsReadRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_event(self, event_id: UUID) -> Optional[dict]:
        query = text("""
            SELECT
                e.id as event_id,
                e.external_id,
                l.key as league_key,
                l.name as league_name,
                t1.name as home_team,
                t2.name as away_team,
                e.commence_time,
                e.status
            FROM events e
            JOIN leagues l ON e.league_id = l.id
            JOIN teams t1 ON e.home_team_id = t1.id
            JOIN teams t2 ON e.away_team_id = t2.id
            WHERE e.id = :event_id
        """)

        result = await self.session.execute(query, {"event_id": event_id})
        row = result.fetchone()

        if not row:
            logger.warning("event_not_found", event_id=str(event_id))
            return None

        return dict(row._mapping)

    async def get_odds_context(self, event_id: UUID) -> Optional[dict]:
        query = text("""
            SELECT
                home_odds_avg,
                away_odds_avg,
                draw_odds_avg,
                home_odds_best,
                away_odds_best,
                draw_odds_best,
                bookmakers_count,
                timestamp_source
            FROM normalized_odds
            WHERE event_id = :event_id AND market_type = 'h2h'
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = await self.session.execute(query, {"event_id": event_id})
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

