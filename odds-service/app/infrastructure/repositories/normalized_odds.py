from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.orm_models import NormalizedOdds
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class NormalizedOddsRepository(BaseRepository[NormalizedOdds]):
    def __init__(self, session: AsyncSession):
        super().__init__(NormalizedOdds, session)

    async def create_normalized(
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
        normalized = NormalizedOdds(
            event_id=event_id,
            market_type=market_type,
            home_odds_avg=home_odds_avg,
            away_odds_avg=away_odds_avg,
            draw_odds_avg=draw_odds_avg,
            home_odds_best=home_odds_best,
            away_odds_best=away_odds_best,
            draw_odds_best=draw_odds_best,
            bookmakers_count=bookmakers_count,
            timestamp_source=timestamp_source,
            timestamp_ingested=timestamp_ingested,
            timestamp_normalized=now_utc()
        )
        normalized = await self.create(normalized)
        logger.info(
            "normalized_odds_created",
            event_id=str(event_id),
            market_type=market_type,
            id=str(normalized.id)
        )
        return normalized.id

    async def get_by_event(
        self,
        event_id: UUID,
        market_type: Optional[str] = None
    ) -> List[NormalizedOdds]:
        query = select(NormalizedOdds).where(NormalizedOdds.event_id == event_id)

        if market_type:
            query = query.where(NormalizedOdds.market_type == market_type)

        query = query.order_by(NormalizedOdds.timestamp_normalized.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_event(
        self, event_id: UUID, market_type: str
    ) -> Optional[NormalizedOdds]:
        result = await self.session.execute(
            select(NormalizedOdds)
            .where(
                and_(
                    NormalizedOdds.event_id == event_id,
                    NormalizedOdds.market_type == market_type
                )
            )
            .order_by(NormalizedOdds.timestamp_normalized.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_normalized_snapshots(
        self, limit: int = 100, competition_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if competition_key:
            query = text("""
                SELECT
                    n.*,
                    e.external_id,
                    l.key as competition_key,
                    t1.name as home_team,
                    t2.name as away_team,
                    e.commence_time
                FROM normalized_odds n
                JOIN events e ON n.event_id = e.id
                JOIN competition l ON e.competition = l.id
                JOIN teams t1 ON e.home_team_id = t1.id
                JOIN teams t2 ON e.away_team_id = t2.id
                WHERE l.key = :competition_key
                ORDER BY n.timestamp_normalized DESC
                LIMIT :limit
            """)
            result = await self.session.execute(query, {"competition_key": competition_key, "limit": limit})
        else:
            query = text("""
                SELECT
                    n.*,
                    e.external_id,
                    l.key as competition_key,
                    t1.name as home_team,
                    t2.name as away_team,
                    e.commence_time
                FROM normalized_odds n
                JOIN events e ON n.event_id = e.id
                JOIN competitions l ON e.competition_id = l.id
                JOIN teams t1 ON e.home_team_id = t1.id
                JOIN teams t2 ON e.away_team_id = t2.id
                ORDER BY n.timestamp_normalized DESC
                LIMIT :limit
            """)
            result = await self.session.execute(query, {"limit": limit})

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
