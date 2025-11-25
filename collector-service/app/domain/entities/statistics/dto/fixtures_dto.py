from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID


class PreparedFixtureRowDTO(BaseModel):
    api_home_id: int
    api_away_id: int
    goals_home: int
    goals_away: int
    match_date: datetime
    compact_raw_payload: Dict[str, Any]


class PreparedFixturesDTO(BaseModel):
    api_team_ids: List[int]
    raw_fixtures_rows: List[PreparedFixtureRowDTO]


class EloFixtureRecordDTO(BaseModel):
    team_id: UUID
    opponent_id: UUID
    competition_id: UUID
    season: int
    match_date: datetime
    goals_for: int
    goals_against: int
    is_home: bool
    raw_payload: Dict[str, Any]

