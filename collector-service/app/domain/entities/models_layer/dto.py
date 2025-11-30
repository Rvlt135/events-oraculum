from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.models_layer.elo_model import EloModelDTO
from app.domain.entities.models_layer.poisson_model import PoissonModelDTO


class ModelScopesDTO(BaseModel):
    elo_outputs: dict[UUID, EloModelDTO]
    poisson_outputs: dict[UUID, PoissonModelDTO]