"""
Builder for building Poisson model features
"""
import math
from uuid import UUID

import structlog

from app.domain.entities.models_layer.poisson_model import PoissonInputFeaturesDTO, PoissonModelDTO

logger = structlog.get_logger()


class PoissonModelBuilder:
    """Builder for Poisson model predictions for football fixtures."""

    def _poisson_pmf(self, lmbd: float, g: int) -> float:
        """Calculate Poisson probability mass function.
        
        Args:
            lmbd: Lambda parameter (expected value).
            g: Number of goals.
            
        Returns:
            Probability of exactly g goals.
        """
        if lmbd <= 0:
            return 0.0
        return (lmbd ** g) * math.exp(-lmbd) / math.factorial(g)

    def build_for_fixtures(
        self,
        input: PoissonInputFeaturesDTO,
    ) -> list[PoissonModelDTO]:
        """Build Poisson model predictions for fixtures.
        
        Args:
            input: Input features containing events, team features, match features, and Poisson features.
            
        Returns:
            List of Poisson model predictions for each event.
        """
        logger.debug("poisson_build_started")
        
        events = input.events
        team_features = input.team_features
        match_features = input.match_features
        poisson_features_f3 = input.poisson_features
        
        if not events:
            logger.debug("poisson_build_empty_events")
            return []
        
        logger.debug("poisson_build_processing", number_of_events=len(events))
        
        results: list[PoissonModelDTO] = []
        
        for event in events:
            # home_id = event.home_team_id # don t user in algorithm
            # away_id = event.away_team_id # don t user in algorithm
            event_id = event.event_id

            # home_tf = team_features[home_id] # don t user in algorithm
            # away_tf = team_features[away_id] # don t user in algorithm

            base = poisson_features_f3[event_id]
            lambda_home_base = base.lambda_home
            lambda_away_base = base.lambda_away
            
            # Compute λ values with minimum threshold
            lambda_home = max(lambda_home_base, 0.01)
            lambda_away = max(lambda_away_base, 0.01)
            
            # Generate Poisson distributions for goals 0..6
            goal_probs_home = [self._poisson_pmf(lambda_home, g) for g in range(7)]
            goal_probs_away = [self._poisson_pmf(lambda_away, g) for g in range(7)]
            
            # Compute outcome probabilities using 7×7 matrix
            p_home = 0.0
            p_draw = 0.0
            p_away = 0.0
            
            for i in range(7):  # home goals
                for j in range(7):  # away goals
                    p = goal_probs_home[i] * goal_probs_away[j]
                    if i > j:
                        p_home += p
                    elif i == j:
                        p_draw += p
                    else:  # i < j
                        p_away += p
            
            # Fair odds with division by zero protection
            fair_home = 1.0 / p_home if p_home > 0 else float("inf")
            fair_draw = 1.0 / p_draw if p_draw > 0 else float("inf")
            fair_away = 1.0 / p_away if p_away > 0 else float("inf")
            
            dto = PoissonModelDTO(
                event_id=event_id,
                competition_id=event.competition_id,
                season=event.season,
                goal_probs_home=goal_probs_home,
                goal_probs_away=goal_probs_away,
                p_home=p_home,
                p_draw=p_draw,
                p_away=p_away,
                fair_home=fair_home,
                fair_draw=fair_draw,
                fair_away=fair_away,
            )
            results.append(dto)
        
        logger.debug("poisson_build_completed", count=len(results))
        return results
