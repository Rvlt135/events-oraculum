from typing import List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.db.orm.fixtures_football_history import FixturesFootballHistory
from app.domain.entities.statistics.dto.fixtures_dto import FixtureHistoryRecordDTO, FixtureHistoryRowDTO, \
    UpcomingFixtureDTO
from app.infrastructure.repositories.base import BaseRepository
from app.utils.time_utils import now_utc
import structlog

logger = structlog.get_logger()


class FixturesFootballRepository(BaseRepository[FixturesFootballHistory]):
    def __init__(self, session: AsyncSession):
        super().__init__(FixturesFootballHistory, session)

    async def bulk_upsert_fixtures(self, records: list[FixtureHistoryRecordDTO]) -> int:
        """Bulk upsert fixtures history."""
        if not records:
            return 0
        
        values = [
            {
                "api_fixture_id": r.api_fixture_id,
                "competition_id": r.competition_id,
                "season": r.season,
                "match_date": r.match_date,
                "home_team_id": r.home_team_id,
                "away_team_id": r.away_team_id,
                "home_goals": r.home_goals,
                "away_goals": r.away_goals,
                "result": r.result,
                "raw_payload": r.raw_payload,
            }
            for r in records
        ]
        
        stmt = insert(FixturesFootballHistory).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fixtures_football_history_api_fixture_id",
            set_={
                "competition_id": stmt.excluded.competition_id,
                "season": stmt.excluded.season,
                "match_date": stmt.excluded.match_date,
                "home_team_id": stmt.excluded.home_team_id,
                "away_team_id": stmt.excluded.away_team_id,
                "home_goals": stmt.excluded.home_goals,
                "away_goals": stmt.excluded.away_goals,
                "result": stmt.excluded.result,
                "raw_payload": stmt.excluded.raw_payload,
            }
        )
        
        await self.session.execute(stmt)
        return len(values)

    async def get_by_competition(self, competition_id: UUID,  season: int) -> List[FixtureHistoryRowDTO]:
        """Get fixtures by competition and season, ordered by match date."""
        result = await self.session.execute(
            select(FixturesFootballHistory)
            .where(and_(
                FixturesFootballHistory.competition_id == competition_id,
                FixturesFootballHistory.season == season)
            )
            .order_by(FixturesFootballHistory.match_date.asc())
        )
        rows = result.scalars().all()
        return [
            FixtureHistoryRowDTO(
                id=row.id,
                api_fixture_id=row.api_fixture_id,
                match_date=row.match_date,
                home_team_id=row.home_team_id,
                away_team_id=row.away_team_id,
                home_goals=row.home_goals,
                away_goals=row.away_goals,
                result=row.result
            )
            for row in rows
        ]

    async def get_upcoming_fixtures(self, competition_id: UUID, season: int) -> List[UpcomingFixtureDTO]:
        """Get upcoming fixtures for competition and season, ordered by match date.
        
        Args:
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            List of upcoming fixture DTOs.
        """
        logger.debug("get_upcoming_fixtures_called", competition_id=str(competition_id), season=season)
        current_time = now_utc()
        result = await self.session.execute(
            select(FixturesFootballHistory)
            .where(and_(
                FixturesFootballHistory.competition_id == competition_id,
                FixturesFootballHistory.season == season,
                FixturesFootballHistory.match_date > current_time
            ))
            .order_by(FixturesFootballHistory.match_date.asc())
        )
        rows = result.scalars().all()
        fixtures = [
            UpcomingFixtureDTO( # TODO: исправить реализацию, здесь нет еще event_id
                fixture_id=row.id,
                match_date=row.match_date,
                home_team_id=row.home_team_id,
                away_team_id=row.away_team_id,
                competition_id=row.competition_id,
                season=row.season
            )
            for row in rows
        ]
        logger.debug("get_upcoming_fixtures_result", competition_id=str(competition_id), season=season, rows_count=len(fixtures))
        return fixtures