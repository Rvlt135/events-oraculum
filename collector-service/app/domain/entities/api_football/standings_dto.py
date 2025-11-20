from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any
from datetime import datetime


# Model team
class Team(BaseModel):
    id: int
    name: str
    logo: str


# Model statistics team
class Goals(BaseModel):
    for_: int = Field(alias='for')
    against: int


# Model statistics match
class MatchStats(BaseModel):
    played: int
    win: int
    draw: int
    lose: int
    goals: Goals


# Model standing position
class StandingPosition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rank: int
    team: Team
    points: int
    goals_diff: int = Field(alias='goalsDiff')
    group: str
    form: str
    status: str
    description: Optional[str] = None
    all: MatchStats
    home: MatchStats
    away: MatchStats
    update: datetime


# Model league
class League(BaseModel):
    id: int
    name: str
    country: str
    logo: str
    flag: Optional[str] = None
    season: int
    standings: List[List[StandingPosition]]


class StandingsLeague(BaseModel):
    league: League

# Модели для пагинации и метаданных
class Paging(BaseModel):
    current: int
    total: int

class Parameters(BaseModel):
    league: str
    season: str

# Полная модель ответа standings
class StandingsResponse(BaseModel):
    get: str
    parameters: Parameters
    errors: List[Any]
    results: int
    paging: Paging
    response: List[StandingsLeague]