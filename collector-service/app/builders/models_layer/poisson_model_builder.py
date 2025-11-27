"""
Builder for building Poisson model features
"""
from uuid import UUID

import structlog

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.models_layer.elo_model import EloInputFeaturesDTO, EloModelDTO
from app.domain.entities.models_layer.poisson_model import PoissonInputFeaturesDTO

logger = structlog.get_logger()


class EloModelBuilder:



    def build_for_fixtures(
        self,
        features: EloInputFeaturesDTO,
    ) -> list[PoissonInputFeaturesDTO]:
        pass
