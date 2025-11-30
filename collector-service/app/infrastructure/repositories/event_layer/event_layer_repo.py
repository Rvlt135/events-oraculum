from typing import List
from uuid import UUID
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.models_layer.elo_model import EloModelDTO
from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.db.orm.models_layer.elo_model import EloModel

logger = structlog.get_logger()

class EventLayerRepository(BaseRepository[EloModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(EloModel, session)