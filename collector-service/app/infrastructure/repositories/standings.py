from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.standings_football import StandingsFootball
from app.domain.entities.statistics.dto.standings_dto import EnrichedStandingRowDTO
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository
from sqlalchemy.dialects.postgresql import insert

logger = structlog.get_logger()


class StandingsFootballRepository(BaseRepository[StandingsFootball]):
    def __init__(self, session: AsyncSession):
        super().__init__(StandingsFootball, session)

    async def bulk_upsert(self, records: List[EnrichedStandingRowDTO]) -> int:
        """
        Bulk upsert standings records.
        
        Args:
            records: List of EnrichedStandingRowDTO records
            
        Returns:
            Number of processed records
        """
        if not records:
            return 0
        
        values = []
        for record in records:
            values.append({
                "team_id": record.team_id,
                "competition_id": record.competition_id,
                "season": record.season,
                "rank": record.rank,
                "points": record.points,
                "goal_diff": record.goal_diff,
                "all_played": record.all_played,
                "all_win": record.all_win,
                "all_draw": record.all_draw,
                "all_lose": record.all_lose,
                "all_goals_for": record.all_goals_for,
                "all_goals_against": record.all_goals_against,
                "home_played": record.home_played,
                "home_win": record.home_win,
                "home_draw": record.home_draw,
                "home_lose": record.home_lose,
                "home_goals_for": record.home_goals_for,
                "home_goals_against": record.home_goals_against,
                "away_played": record.away_played,
                "away_win": record.away_win,
                "away_draw": record.away_draw,
                "away_lose": record.away_lose,
                "away_goals_for": record.away_goals_for,
                "away_goals_against": record.away_goals_against,
                "form_raw": record.form_raw,
                "status": record.status,
                "raw_payload": record.raw_payload,
            })
        
        stmt = insert(StandingsFootball).values(values)
        
        stmt = stmt.on_conflict_do_update(
            constraint="uq_standings_football_team_competition_season",
            set_={
                "rank": stmt.excluded.rank,
                "points": stmt.excluded.points,
                "goal_diff": stmt.excluded.goal_diff,
                "all_played": stmt.excluded.all_played,
                "all_win": stmt.excluded.all_win,
                "all_draw": stmt.excluded.all_draw,
                "all_lose": stmt.excluded.all_lose,
                "all_goals_for": stmt.excluded.all_goals_for,
                "all_goals_against": stmt.excluded.all_goals_against,
                "home_played": stmt.excluded.home_played,
                "home_win": stmt.excluded.home_win,
                "home_draw": stmt.excluded.home_draw,
                "home_lose": stmt.excluded.home_lose,
                "home_goals_for": stmt.excluded.home_goals_for,
                "home_goals_against": stmt.excluded.home_goals_against,
                "away_played": stmt.excluded.away_played,
                "away_win": stmt.excluded.away_win,
                "away_draw": stmt.excluded.away_draw,
                "away_lose": stmt.excluded.away_lose,
                "away_goals_for": stmt.excluded.away_goals_for,
                "away_goals_against": stmt.excluded.away_goals_against,
                "form_raw": stmt.excluded.form_raw,
                "status": stmt.excluded.status,
                "raw_payload": stmt.excluded.raw_payload,
                "updated_at": now_utc(),
            }
        )
        
        await self.session.execute(stmt)
        
        logger.info(
            "standings_bulk_upserted",
            count=len(records)
        )
        
        return len(records)

    async def get_by_competition(self, league_id, season):
        NotImplemented()