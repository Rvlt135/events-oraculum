from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.infrastructure.db.orm.fixtures_football_history import FixturesFootballHistory
from app.infrastructure.repositories.base import BaseRepository


class TeamFeaturesRepository(BaseRepository[FixturesFootballHistory]):
    def __init__(self, session: AsyncSession):
        super().__init__(FixturesFootballHistory, session)

    def bulk_upsert_team_features(self, features: list[TeamFeaturesDTO]):
        NotImplemented()
