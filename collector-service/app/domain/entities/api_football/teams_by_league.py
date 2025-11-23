from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# Модель команды
class Team(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    country: str
    founded: Optional[int] = None
    national: bool
    logo: str

# Модель стадиона
class Venue(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    capacity: Optional[int] = None
    surface: Optional[str] = None
    image: Optional[str] = None

# Модель элемента response (команда + стадион)
class TeamVenue(BaseModel):
    team: Team
    venue: Optional[Venue] = None

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