from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from app.infrastructure.db.orm.feature_layer.match_features import MatchFeatures
from app.infrastructure.repositories.base import BaseRepository


class MatchFeaturesRepository(BaseRepository[MatchFeatures]):
    def __init__(self, session: AsyncSession):
        super().__init__(MatchFeatures, session)