from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
import structlog

from app.infrastructure.db.orm.fixtures_football_history import FixturesFootballHistory
from app.domain.entities.statistics.dto.fixtures_dto import EloFixtureRecordDTO
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class FixturesFootballRepository(BaseRepository[FixturesFootballHistory]):
    def __init__(self, session: AsyncSession):
        super().__init__(FixturesFootballHistory, session)

    async def bulk_upsert_fixtures(self, records: list[EloFixtureRecordDTO]) -> int:
        """Bulk upsert fixtures history for Elo."""
        if not records:
            return 0
        
        fixture_map = {}
        for r in records:
            key = (r.competition_id, r.season, r.match_date, min(r.team_id, r.opponent_id), max(r.team_id, r.opponent_id))
            if key not in fixture_map:
                fixture_map[key] = {
                    "competition_id": r.competition_id,
                    "season": r.season,
                    "match_date": r.match_date,
                    "raw_payload": r.raw_payload,
                }
            
            if r.is_home:
                fixture_map[key]["home_team_id"] = r.team_id
                fixture_map[key]["away_team_id"] = r.opponent_id
                fixture_map[key]["home_goals"] = r.goals_for
                fixture_map[key]["away_goals"] = r.goals_against
            else:
                fixture_map[key]["home_team_id"] = r.opponent_id
                fixture_map[key]["away_team_id"] = r.team_id
                fixture_map[key]["home_goals"] = r.goals_against
                fixture_map[key]["away_goals"] = r.goals_for
        
        values = []
        for data in fixture_map.values():
            home_goals = data["home_goals"]
            away_goals = data["away_goals"]
            if home_goals > away_goals:
                result = 1
            elif home_goals < away_goals:
                result = -1
            else:
                result = 0
            
            payload = data["raw_payload"]
            api_fixture_id = None
            if isinstance(payload, dict):
                api_fixture_id = payload.get("fixture_id")
            
            if not api_fixture_id:
                continue
            
            values.append({
                "api_fixture_id": api_fixture_id,
                "competition_id": data["competition_id"],
                "season": data["season"],
                "match_date": data["match_date"],
                "home_team_id": data["home_team_id"],
                "away_team_id": data["away_team_id"],
                "home_goals": home_goals,
                "away_goals": away_goals,
                "result": result,
                "raw_payload": payload,
            })
        
        if not values:
            return 0

        # TODO: Remove after debugging - log api_fixture_id to locate duplicates
        api_fixture_ids = [v["api_fixture_id"] for v in values]
        api_fixture_ids_sorted = sorted(api_fixture_ids)
        logger.warning(
            "bulk_upsert_fixtures_debug",
            api_fixture_ids=api_fixture_ids_sorted,
            total_count=len(api_fixture_ids),
            unique_count=len(set(api_fixture_ids)),
            duplicates=[x for x in api_fixture_ids_sorted if api_fixture_ids_sorted.count(x) > 1]
        )
        
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

