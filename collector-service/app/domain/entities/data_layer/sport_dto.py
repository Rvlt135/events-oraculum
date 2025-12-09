from pydantic import BaseModel

from app.domain.entities.data_layer.competition import CompetitionEntity


class SportDTO(BaseModel):
    provider: str = "odds_api"
    category: str  # normalized slug_key
    is_active: bool
    plan_visibility: str  # computed via policy


class SportsAndCompetitionsDTO(BaseModel):
    sports: list[SportDTO]
    competitions: list[CompetitionEntity]