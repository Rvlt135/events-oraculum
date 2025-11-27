"""
Builder for building poisson features
"""
from typing import List
from uuid import UUID

import structlog

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import FixtureHistoryRowDTO, LastFixtureDTO, UpcomingFixtureDTO

logger = structlog.get_logger()


class PoissonFeaturesBuilder:
    """Builder for Poisson distribution features for football fixtures."""
    
    def __init__(self, home_advantage: float = 1.1):
        """Initialize builder with home advantage factor.
        
        Args:
            home_advantage: Multiplier for home team lambda (default: 1.1).
        """
        self.home_advantage = home_advantage

    def build_for_fixtures(
        self,
        fixtures: list[UpcomingFixtureDTO],
        team_features: dict[UUID, TeamFeaturesDTO],
        match_features: dict[UUID, MatchFeaturesDTO],
    ) -> list[PoissonFeaturesDTO]:
        """Build Poisson features for upcoming fixtures.
        
        Args:
            fixtures: List of upcoming fixtures.
            team_features: Dictionary mapping team_id to TeamFeaturesDTO.
            match_features: Dictionary mapping team_id to MatchFeaturesDTO.
            
        Returns:
            List of PoissonFeaturesDTO for each fixture.
        """
        logger.debug("build_for_fixtures_called", fixtures_count=len(fixtures))
        if not fixtures:
            logger.debug("build_for_fixtures_empty_fixtures")
            return []
        
        result = []
        
        for fixture in fixtures:
            # Read team and match features
            home_tf = team_features[fixture.home_team_id]
            away_tf = team_features[fixture.away_team_id]
            home_mf = match_features[fixture.home_team_id]
            away_mf = match_features[fixture.away_team_id]
            
            # Compute initial lambda values
            lambda_home = home_tf.goals_for_avg
            lambda_away = away_tf.goals_for_avg
            mu_home = home_tf.goals_against_avg
            mu_away = away_tf.goals_against_avg
            
            # Adjust lambda with form
            lambda_home *= (1 + home_mf.avg_goals_for_last_n / 10)
            lambda_away *= (1 + away_mf.avg_goals_for_last_n / 10)
            
            # Apply home advantage
            lambda_home *= self.home_advantage
            
            # Apply strength ratio
            strength_ratio = home_tf.strength_initial / max(away_tf.strength_initial, 1)
            lambda_home *= strength_ratio
            lambda_away /= strength_ratio
            
            # Expected goals
            expected_goals_home = lambda_home
            expected_goals_away = lambda_away
            
            # Build DTO
            poisson_feature = PoissonFeaturesDTO(
                event_id=fixture.event_id,
                home_team_id=fixture.home_team_id,
                away_team_id=fixture.away_team_id,
                competition_id=fixture.competition_id,
                season=fixture.season,
                lambda_home=lambda_home,
                lambda_away=lambda_away,
                home_strength=home_tf.strength_initial,
                away_strength=away_tf.strength_initial,
                expected_goals_home=expected_goals_home,
                expected_goals_away=expected_goals_away,
            )
            result.append(poisson_feature)
        
        logger.debug("build_for_fixtures_completed", built_count=len(result))
        return result