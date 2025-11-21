from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# Модель команды
class Team(BaseModel):
    id: int
    name: str
    code: str
    country: str
    founded: int
    national: bool
    logo: str

# Модель стадиона
class Venue(BaseModel):
    id: int
    name: str
    address: str
    city: str
    capacity: int
    surface: str
    image: str

# Модель элемента response (команда + стадион)
class TeamVenue(BaseModel):
    team: Team
    venue: Venue

# Модель пагинации
class Paging(BaseModel):
    current: int
    total: int

# Модель параметров запроса
class Parameters(BaseModel):
    league: str
    season: str

# Основная модель ответа
class TeamsResponse(BaseModel):
    get: str
    parameters: Parameters
    errors: List[str]  # или List[Any] если могут быть разные типы ошибок
    results: int
    paging: Paging
    response: List[TeamVenue]