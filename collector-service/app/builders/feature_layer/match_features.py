"""
Builder for building match features
"""
from typing import List
from uuid import UUID

import structlog

from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.statistics.dto.standings_dto import StandingMinimalDTO
from app.infrastructure.db.orm.standings_football import StandingsFootball

logger = structlog.get_logger()


class MatchFeaturesBuilder:
    NotImplemented()