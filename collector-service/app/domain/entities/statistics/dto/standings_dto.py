from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class StandingRowDTO(BaseModel):
    api_team_id: int
    rank: int
    points: int
    goal_diff: int
    all_played: int
    all_win: int
    all_draw: int
    all_lose: int
    all_goals_for: int
    all_goals_against: int
    home_played: int
    home_win: int
    home_draw: int
    home_lose: int
    home_goals_for: int
    home_goals_against: int
    away_played: int
    away_win: int
    away_draw: int
    away_lose: int
    away_goals_for: int
    away_goals_against: int
    form_raw: str
    status: str
    update: datetime


class StandingPreparedData(BaseModel):
    api_team_ids: List[int]
    raw_standings_rows: List[StandingRowDTO]


class StandingsTeamMap(BaseModel):
    api_team_id: int
    team_id: UUID


class EnrichedStandingRowDTO(BaseModel):
    team_id: UUID
    competition_id: UUID
    season: int
    rank: int
    points: int
    goal_diff: int
    all_played: int
    all_win: int
    all_draw: int
    all_lose: int
    all_goals_for: int
    all_goals_against: int
    home_played: int
    home_win: int
    home_draw: int
    home_lose: int
    home_goals_for: int
    home_goals_against: int
    away_played: int
    away_win: int
    away_draw: int
    away_lose: int
    away_goals_for: int
    away_goals_against: int
    form_raw: Optional[str] = None
    status: Optional[str] = None
    raw_payload: dict
