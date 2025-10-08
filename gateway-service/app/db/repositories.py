from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()


class RecommendationsReadRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_recommendations(
        self,
        league: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        query = text("""
            SELECT
                rec_id, event_id, league_key, pick, confidence,
                short_explanation, model_version, created_ts
            FROM recommendations
            WHERE 1=1
        """)

        count_query = text("SELECT COUNT(*) FROM recommendations WHERE 1=1")

        filters = []
        params = {"limit": limit, "offset": offset}

        if league:
            filters.append(" AND league_key = :league")
            params["league"] = league

        if from_date:
            filters.append(" AND created_ts >= :from_date")
            params["from_date"] = from_date

        if to_date:
            filters.append(" AND created_ts <= :to_date")
            params["to_date"] = to_date

        if min_confidence is not None:
            filters.append(" AND confidence >= :min_conf")
            params["min_conf"] = min_confidence

        filter_clause = "".join(filters)

        full_query = text(str(query) + filter_clause + " ORDER BY created_ts DESC LIMIT :limit OFFSET :offset")
        full_count_query = text(str(count_query) + filter_clause)

        result = await self.session.execute(full_query, params)
        rows = result.fetchall()

        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
        count_result = await self.session.execute(full_count_query, count_params)
        total = count_result.scalar() or 0

        recommendations = [dict(row._mapping) for row in rows]

        logger.info("recommendations_fetched", count=len(recommendations), total=total)

        return recommendations, total

    async def get_by_event_id(self, event_id: UUID) -> List[dict]:
        query = text("""
            SELECT
                rec_id, event_id, league_key, pick, confidence,
                short_explanation, model_version, created_ts
            FROM recommendations
            WHERE event_id = :event_id
            ORDER BY created_ts DESC
        """)

        result = await self.session.execute(query, {"event_id": event_id})
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def get_stats(
        self,
        league: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        query = text("""
            SELECT
                COUNT(*) as count_recommendations,
                COUNT(DISTINCT event_id) as baseline_count,
                MAX(created_ts) as latest_recommendation_ts
            FROM recommendations
            WHERE 1=1
        """)

        pick_dist_query = text("""
            SELECT pick, COUNT(*) as count
            FROM recommendations
            WHERE 1=1
        """)

        filters = []
        params = {}

        if league:
            filters.append(" AND league_key = :league")
            params["league"] = league

        if from_date:
            filters.append(" AND created_ts >= :from_date")
            params["from_date"] = from_date

        if to_date:
            filters.append(" AND created_ts <= :to_date")
            params["to_date"] = to_date

        filter_clause = "".join(filters)

        full_query = text(str(query) + filter_clause)
        full_pick_query = text(str(pick_dist_query) + filter_clause + " GROUP BY pick")

        result = await self.session.execute(full_query, params)
        stats_row = result.fetchone()

        pick_result = await self.session.execute(full_pick_query, params)
        pick_rows = pick_result.fetchall()

        distribution = {row.pick: row.count for row in pick_rows}

        stats = {
            "count_recommendations": stats_row.count_recommendations if stats_row else 0,
            "baseline_count": stats_row.baseline_count if stats_row else 0,
            "latest_recommendation_ts": stats_row.latest_recommendation_ts if stats_row else None,
            "distribution_by_pick": distribution,
        }

        logger.info("stats_fetched", stats=stats)

        return stats


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
