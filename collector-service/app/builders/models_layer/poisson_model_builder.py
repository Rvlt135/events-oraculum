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
        
        Pure probabilistic layer: uses lambda values from PoissonFeaturesBuilder (F3)
        without reapplying football logic. Acts as a probabilistic transformer.
        
        Args:
            input: PoissonInputFeaturesDTO Input features containing events, team features, match features, and Poisson features.
            
        Returns:
            List of Poisson model predictions for each event.
        """
        events = input.events
        poisson_features_f3 = input.poisson_features
        
        # Input validation: empty events
        if not events:
            logger.debug("poisson_build_empty_events")
            return []
        
        logger.debug("poisson_build_started", events_count=len(events))
        
        results: list[PoissonModelDTO] = []
        
        for event in events:
            event_id = event.event_id
            
            # Input validation: missing event_id in poisson_features
            if event_id not in poisson_features_f3:
                logger.debug("poisson_build_skip_missing_features", event_id=str(event_id))
                continue
            
            # Get lambda values from F3 (already stabilized)
            base = poisson_features_f3[event_id]
            lambda_home = base.lambda_home
            lambda_away = base.lambda_away
            
            # Sanity guard: soft clamp to expected range [0.2, 3.5] with warning
            lambda_home_raw = lambda_home
            lambda_away_raw = lambda_away
            sanity_guard_triggered = False
            
            if lambda_home < 0.2 or lambda_home > 3.5:
                lambda_home = max(0.2, min(3.5, lambda_home))
                sanity_guard_triggered = True
            if lambda_away < 0.2 or lambda_away > 3.5:
                lambda_away = max(0.2, min(3.5, lambda_away))
                sanity_guard_triggered = True
            
            if sanity_guard_triggered:
                logger.debug(
                    "poisson_lambda_sanity_guard",
                    event_id=str(event_id),
                    lambda_home_raw=lambda_home_raw,
                    lambda_away_raw=lambda_away_raw,
                    lambda_home=lambda_home,
                    lambda_away=lambda_away,
                )
            
            # Generate Poisson distributions for goals 0..8 (extended range to reduce tail loss)
            goal_probs_home = [self._poisson_pmf(lambda_home, g) for g in range(9)]
            goal_probs_away = [self._poisson_pmf(lambda_away, g) for g in range(9)]
            
            # Compute outcome probabilities using 9×9 matrix multiplication
            p_home = 0.0
            p_draw = 0.0
            p_away = 0.0
            
            for i in range(9):  # home goals
                for j in range(9):  # away goals
                    p = goal_probs_home[i] * goal_probs_away[j]
                    if i > j:
                        p_home += p
                    elif i == j:
                        p_draw += p
                    else:  # i < j
                        p_away += p
            
            # Sanity checks (diagnostic only, no auto-correction)
            prob_sum = p_home + p_draw + p_away
            prob_deviation = abs(prob_sum - 1.0)
            has_invalid_prob = (p_home < 0 or p_home > 1 or 
                               p_draw < 0 or p_draw > 1 or 
                               p_away < 0 or p_away > 1)
            
            if prob_deviation > 0.005 or has_invalid_prob:
                logger.debug(
                    "poisson_probability_sanity_check",
                    event_id=str(event_id),
                    prob_sum=prob_sum,
                    prob_deviation=prob_deviation,
                    p_home=p_home,
                    p_draw=p_draw,
                    p_away=p_away,
                    has_invalid_prob=has_invalid_prob,
                )
            
            # Fair odds with division by zero protection
            fair_home = 1.0 / p_home if p_home > 0 else float("inf")
            fair_draw = 1.0 / p_draw if p_draw > 0 else float("inf")
            fair_away = 1.0 / p_away if p_away > 0 else float("inf")
            
            # DTO construction: expected_goals mirror lambda (already in PoissonFeaturesDTO)
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
        
        logger.debug("poisson_build_completed", results_count=len(results))
        return results
