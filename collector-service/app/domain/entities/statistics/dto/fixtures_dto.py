from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID


class PreparedFixtureRowDTO(BaseModel):
    api_fixture_id: int
    api_home_id: int
    api_away_id: int
    goals_home: int
    goals_away: int
    match_date: datetime
    compact_raw_payload: Dict[str, Any]


class PreparedFixturesDTO(BaseModel):
    api_team_ids: List[int]
    raw_fixtures_rows: List[PreparedFixtureRowDTO]

# TODO: For feature elo move
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

class FixtureHistoryRecordDTO(BaseModel):
    api_fixture_id: int
    competition_id: UUID
    season: int
    match_date: datetime
    home_team_id: UUID
    away_team_id: UUID
    home_goals: int
    away_goals: int
    result: int          # -1/0/1 для home
    raw_payload: dict

class FixtureHistoryRowDTO(BaseModel):
    id: UUID
    api_fixture_id: int
    match_date: datetime
    home_team_id: UUID
    away_team_id: UUID
    home_goals: int
    away_goals: int
    result: int

