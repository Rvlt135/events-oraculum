"""
Builder for building poisson features
"""
from typing import List
from uuid import UUID
import math

import structlog

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.feature_layer.poisson_features_dto import PoissonFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import FixtureHistoryRowDTO, LastFixtureDTO, UpcomingFixtureDTO

logger = structlog.get_logger()


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


class PoissonFeaturesBuilder:
    """Builder for Poisson distribution features for football fixtures."""
    
    # Global baseline constants (temporary "average league" baselines)
    BASE_GOALS_HOME = 1.35
    BASE_GOALS_AWAY = 1.05
    
    # Global averages for attack/defense normalization
    AVG_GF = 1.35
    AVG_GA = 1.35
    
    def __init__(self, home_advantage: float = 1.08):
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
            
            # Start from global baselines (not from goals_for_avg)
            lambda_home = self.BASE_GOALS_HOME
            lambda_away = self.BASE_GOALS_AWAY
            
            # Compute attack/defense factors (mild multiplicative, capped)
            attack_home = clamp(home_tf.goals_for_avg / self.AVG_GF, 0.7, 1.3)
            def_away = clamp(away_tf.goals_against_avg / self.AVG_GA, 0.7, 1.3)
            attack_away = clamp(away_tf.goals_for_avg / self.AVG_GF, 0.7, 1.3)
            def_home = clamp(home_tf.goals_against_avg / self.AVG_GA, 0.7, 1.3)
            
            # Apply attack/defense factors
            lambda_home *= attack_home * def_away
            lambda_away *= attack_away * def_home
            
            # Apply mild symmetric strength factor (log-scaled and capped)
            raw_strength_ratio = home_tf.strength_initial / max(away_tf.strength_initial, 1e-6)
            strength_ratio = clamp(raw_strength_ratio, 0.5, 2.0)
            log_ratio = math.log(strength_ratio)
            strength_mult_home = clamp(1.0 + 0.10 * log_ratio, 0.85, 1.15)
            strength_mult_away = clamp(1.0 - 0.10 * log_ratio, 0.85, 1.15)
            lambda_home *= strength_mult_home
            lambda_away *= strength_mult_away
            
            # Apply form/history adjustment (mild, capped, symmetric)
            delta_home = clamp(
                (home_mf.avg_goals_for_last_n - home_tf.goals_for_avg) / 10,
                -0.10, 0.10
            )
            delta_away = clamp(
                (away_mf.avg_goals_for_last_n - away_tf.goals_for_avg) / 10,
                -0.10, 0.10
            )
            lambda_home *= (1.0 + delta_home)
            lambda_away *= (1.0 + delta_away)
            
            # Apply home advantage once (only to home)
            lambda_home *= self.home_advantage
            
            # Track raw values before clamping for logging
            raw_lambda_home = lambda_home
            raw_lambda_away = lambda_away
            
            # Final clamps (must-have for realistic λ range)
            lambda_home = clamp(lambda_home, 0.2, 3.5)
            lambda_away = clamp(lambda_away, 0.2, 3.5)
            
            # Minimal logging if clamp was applied or raw lambda exceeds 3.5
            if raw_lambda_home != lambda_home or raw_lambda_away != lambda_away or raw_lambda_home > 3.5 or raw_lambda_away > 3.5:
                logger.debug(
                    "poisson_lambda_sanity",
                    event_id=fixture.event_id,
                    lambda_home=lambda_home,
                    lambda_away=lambda_away,
                    home_strength=home_tf.strength_initial,
                    away_strength=away_tf.strength_initial,
                )
            
            # Expected goals mirror lambda
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