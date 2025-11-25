from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

# Вложенные модели для fixture
class Periods(BaseModel):
    first: Optional[int] = None
    second: Optional[int] = None

class Venue(BaseModel):
    id: int
    name: str
    city: str

class Status(BaseModel):
    long: str
    short: str
    elapsed: Optional[int] = None
    extra: Optional[int] = None

class Fixture(BaseModel):
    id: int
    referee: Optional[str] = None
    timezone: str
    date: datetime
    timestamp: int
    periods: Periods
    venue: Venue
    status: Status

# Модель для лиги
class League(BaseModel):
    id: int
    name: str
    country: str
    logo: str
    flag: Optional[str] = None
    season: int
    round: str
    standings: bool

# Модели для команд
class TeamResult(BaseModel):
    id: int
    name: str
    logo: str
    winner: Optional[bool] = None

class Teams(BaseModel):
    home: TeamResult
    away: TeamResult

# Модели для счета
class ScorePeriod(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None

class Score(BaseModel):
    halftime: ScorePeriod
    fulltime: ScorePeriod
    extratime: ScorePeriod
    penalty: ScorePeriod

class Goals(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None

# Основная модель для элемента response
class FixtureItem(BaseModel):
    fixture: Fixture
    league: League
    teams: Teams
    goals: Goals
    score: Score

# Существующие модели (можно вынести в общий файл)
class Paging(BaseModel):
    current: int
    total: int

class Parameters(BaseModel):
    league: str
    season: str

# Основная модель ответа fixtures
class FixturesResponse(BaseModel):
    get: str
    parameters: Parameters
    errors: List[str]
    results: int
    paging: Paging
    response: List[FixtureItem]