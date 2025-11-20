from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal


class LocationStats(BaseModel):
    home: int
    away: int
    total: int


class MinuteStats(BaseModel):
    total: Optional[int] = None
    percentage: Optional[str] = None


class UnderOverStats(BaseModel):
    over: int
    under: int


# Модели для голов
class GoalsTotal(BaseModel):
    home: int
    away: int
    total: int


class GoalsAverage(BaseModel):
    home: str
    away: str
    total: str


class GoalsMinute(BaseModel):
    minute_0_15: MinuteStats = Field(alias='0-15')
    minute_16_30: MinuteStats = Field(alias='16-30')
    minute_31_45: MinuteStats = Field(alias='31-45')
    minute_46_60: MinuteStats = Field(alias='46-60')
    minute_61_75: MinuteStats = Field(alias='61-75')
    minute_76_90: MinuteStats = Field(alias='76-90')
    minute_91_105: MinuteStats = Field(alias='91-105')
    minute_106_120: MinuteStats = Field(alias='106-120')


class GoalsUnderOver(BaseModel):
    under_over_0_5: UnderOverStats = Field(alias='0.5')
    under_over_1_5: UnderOverStats = Field(alias='1.5')
    under_over_2_5: UnderOverStats = Field(alias='2.5')
    under_over_3_5: UnderOverStats = Field(alias='3.5')
    under_over_4_5: UnderOverStats = Field(alias='4.5')


class GoalsFor(BaseModel):
    total: GoalsTotal
    average: GoalsAverage
    minute: GoalsMinute
    under_over: GoalsUnderOver


class GoalsAgainst(BaseModel):
    total: GoalsTotal
    average: GoalsAverage
    minute: GoalsMinute
    under_over: GoalsUnderOver


# Модели для фикстур
class FixturesStats(BaseModel):
    played: LocationStats
    wins: LocationStats
    draws: LocationStats
    loses: LocationStats


# Модели для biggest
class BiggestStreak(BaseModel):
    wins: int
    draws: int
    loses: int


class BiggestScore(BaseModel):
    home: Optional[str] = None
    away: Optional[str] = None


class BiggestGoals(BaseModel):
    for_: BiggestScore = Field(alias='for')
    against: BiggestScore


# Модели для карточек
class CardsStats(BaseModel):
    yellow: GoalsMinute
    red: GoalsMinute


# Модели для пенальти
class PenaltyStats(BaseModel):
    total: int
    percentage: str


class Penalty(BaseModel):
    scored: PenaltyStats
    missed: PenaltyStats
    total: int


# Модель для составов
class Lineup(BaseModel):
    formation: str
    played: int


# Основные модели
class League(BaseModel):
    id: int
    name: str
    country: str
    logo: str
    flag: Optional[str] = None
    season: int


class Team(BaseModel):
    id: int
    name: str
    logo: str


class CleanSheet(BaseModel):
    home: int
    away: int
    total: int


class FailedToScore(BaseModel):
    home: int
    away: int
    total: int


class Biggest(BaseModel):
    streak: BiggestStreak
    wins: BiggestScore
    loses: BiggestScore
    goals: BiggestGoals


class Goals(BaseModel):
    for_: GoalsFor = Field(alias='for')
    against: GoalsAgainst


# Основная модель статистики команды
class TeamStatistics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    league: League
    team: Team
    form: str
    fixtures: FixturesStats
    goals: Goals
    biggest: Biggest
    clean_sheet: CleanSheet
    failed_to_score: FailedToScore
    penalty: Penalty
    lineups: List[Lineup]
    cards: CardsStats


# Модели для пагинации и метаданных
class Paging(BaseModel):
    current: int
    total: int


class Parameters(BaseModel):
    season: str
    team: str
    league: str


# Полная модель ответа
class TeamStatisticsResponse(BaseModel):
    get: str
    parameters: Parameters
    errors: List[Any]
    results: int
    paging: Paging
    response: TeamStatistics