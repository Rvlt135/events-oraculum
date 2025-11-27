"""
Builder for building Elo model features
"""
from uuid import UUID

import structlog

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.models_layer.elo_model import EloInputFeaturesDTO, EloModelDTO

logger = structlog.get_logger()


class EloModelBuilder:
    """Builder for Elo model for football fixtures."""
    
    def __init__(self, k_factor: float = 32.0, home_advantage: float = 1.1):
        """Initialize builder with Elo configuration.
        
        Args:
            k_factor: K-factor for Elo rating updates (default: 32.0).
            home_advantage: Home advantage multiplier (default: 1.1).
        """
        self.config = type('Config', (), {
            'k_factor': k_factor,
            'home_advantage': home_advantage
        })()

    def _compute_form_adjustment(
        self,
        mf_home: MatchFeaturesDTO,
        mf_away: MatchFeaturesDTO,
    ) -> float:
        """Compute form adjustment factor based on recent match results.
        
        Args:
            mf_home: Match features for home team.
            mf_away: Match features for away team.
            
        Returns:
            Form adjustment multiplier.
        """
        if not mf_home.form_last_n or not mf_away.form_last_n:
            return 1.0
        
        home_wins = mf_home.form_last_n.count('W')
        home_draws = mf_home.form_last_n.count('D')
        home_form_score = (home_wins * 3 + home_draws) / max(len(mf_home.form_last_n), 1)
        
        away_wins = mf_away.form_last_n.count('W')
        away_draws = mf_away.form_last_n.count('D')
        away_form_score = (away_wins * 3 + away_draws) / max(len(mf_away.form_last_n), 1)
        
        form_diff = home_form_score - away_form_score
        return 1.0 + (form_diff * 0.1)

    def _compute_draw_adjustment(
        self,
        expected_home: float,
        expected_away: float,
    ) -> float:
        """Compute draw probability adjustment.
        
        Args:
            expected_home: Expected result for home team.
            expected_away: Expected result for away team.
            
        Returns:
            Draw adjustment value.
        """
        # Draw probability increases when teams are more evenly matched
        diff = abs(expected_home - expected_away)
        # Maximum draw adjustment when diff is 0, decreases as diff increases
        draw_adjustment = 0.25 * (1.0 - diff)
        return max(0.0, min(0.25, draw_adjustment))

    def build_for_fixtures(
        self,
        features: EloInputFeaturesDTO,
    ) -> list[EloModelDTO]:
        """Build Elo model predictions for fixtures.
        
        Args:
            features: Input features DTO containing events and feature dictionaries.
            
        Returns:
            List of EloModelDTO predictions.
        """
        events = features.events
        team_features = features.team_features
        match_features = features.match_features
        poisson_features = features.poisson_features
        
        results: list[EloModelDTO] = []
        
        for event in events:
            event_id = event.event_id
            home_id = event.home_team_id
            away_id = event.away_team_id
            
            tf_home = team_features.get(home_id)
            tf_away = team_features.get(away_id)
            mf_home = match_features.get(home_id)
            mf_away = match_features.get(away_id)
            pf = poisson_features.get(event_id)
            
            if not all([tf_home, tf_away, mf_home, mf_away, pf]):
                continue
            
            # Pre-Model Normalization
            K = self.config.k_factor
            home_advantage = self.config.home_advantage
            strength_ratio = tf_home.strength_initial / max(tf_away.strength_initial, 1)
            form_adjust = self._compute_form_adjustment(mf_home, mf_away)
            
            # Expected Result Calculation
            rating_diff = strength_ratio * form_adjust * home_advantage
            expected_home = 1 / (1 + 10 ** (-rating_diff / 400))
            expected_away = 1 - expected_home
            draw_adjustment = self._compute_draw_adjustment(expected_home, expected_away)
            
            # Elo Update (prediction mode)
            elo_home_new = expected_home
            elo_away_new = expected_away
            
            # Baseline Probabilities
            p_home = expected_home - 0.5 * draw_adjustment
            p_draw = draw_adjustment
            p_away = expected_away - 0.5 * draw_adjustment
            
            dto = EloModelDTO(
                event_id=event_id,
                elo_home_new=elo_home_new,
                elo_away_new=elo_away_new,
                expected_result_home=expected_home,
                expected_result_away=expected_away,
                draw_adjustment=draw_adjustment,
                p_home=p_home,
                p_draw=p_draw,
                p_away=p_away,
            )
            results.append(dto)
        
        logger.debug("elo_build_completed", count=len(results))
        return results