from typing import List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.db.orm.fixtures_football_history import FixturesFootballHistory
from app.domain.entities.statistics.dto.fixtures_dto import FixtureHistoryRecordDTO, FixtureHistoryRowDTO
from app.infrastructure.repositories.base import BaseRepository


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
