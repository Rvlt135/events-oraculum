from typing import List, Dict, Any
from pydantic import BaseModel
import structlog

from app.agents.base import BaseAgent
from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO

logger = structlog.get_logger()


class RiskSchema(BaseModel):
    """Schema for risk analysis output."""
    score: float  # range [-1, 1], where negative = high risk, positive = low risk
    signals: List[str]


class RiskAgent(BaseAgent):
    """Analyzes betting risk factors and model uncertainty."""
    
    name = "risk_agent"
    model_id = "openai/gpt-4o-mini"
    prompt_name = "risk_analysis"

    def build_prompt(self, input_data: AgentInputDTO) -> Dict[str, Any]:
        """
        Build prompt for risk analysis using PromptProcessor.
        
        Args:
            input_data: AgentInputDTO containing risk-related data
            
        Returns:
            Dictionary with system_prompt, user_prompt, parameters, template_name, template_version
            
        Raises:
            ValueError: If template not found
        """
        bundle = input_data.bundle
        edge = input_data.edge
        
        # Extract from poisson_event_features
        poisson_features = bundle.poisson_event_features
        home_lambda = poisson_features.lambda_home
        away_lambda = poisson_features.lambda_away
        lambda_diff = abs(home_lambda - away_lambda)
        lambda_volatility = abs(home_lambda - away_lambda) / max(home_lambda, away_lambda) if max(home_lambda, away_lambda) > 0 else 0.0
        
        # Extract from elo_output
        elo = bundle.elo_output
        expected_home = elo.expected_home or 0.0
        expected_away = elo.expected_away or 0.0
        elo_uncertainty = abs(expected_home - expected_away)
        
        # Extract from market_odds
        market = bundle.market_odds
        home_gap = abs(market.home_best - market.home_avg) if market.home_avg > 0 else 0.0
        away_gap = abs(market.away_best - market.away_avg) if market.away_avg > 0 else 0.0
        draw_gap = abs(market.draw_best - market.draw_avg) if market.draw_best and market.draw_avg else 0.0
        
        # Extract from edge
        edge_home = edge.edge_home
        edge_away = edge.edge_away
        edge_draw = edge.edge_draw
        negative_edges = sum(1 for e in [edge_home, edge_away, edge_draw] if e < 0)
        
        # Extract from match_history
        home_form = bundle.match_history_home.form_last_n
        away_form = bundle.match_history_away.form_last_n
        home_volatility = self._calculate_streak_volatility(home_form)
        away_volatility = self._calculate_streak_volatility(away_form)
        
        # Build context dict matching template placeholders
        context = {
            "home_lambda": home_lambda,
            "away_lambda": away_lambda,
            "lambda_diff": lambda_diff,
            "lambda_volatility": lambda_volatility,
            "expected_home": expected_home,
            "expected_away": expected_away,
            "elo_uncertainty": elo_uncertainty,
            "home_gap": home_gap,
            "away_gap": away_gap,
            "draw_gap": draw_gap,
            "edge_home": edge_home,
            "edge_away": edge_away,
            "edge_draw": edge_draw,
            "negative_edges": negative_edges,
            "home_form": home_form,
            "away_form": away_form,
            "home_volatility": home_volatility,
            "away_volatility": away_volatility,
        }
        
        logger.debug(
            "building_risk_prompt",
            event_id=str(input_data.event_id),
            home_lambda=home_lambda,
            away_lambda=away_lambda,
        )
        
        prompt_data = self.prompt_processor.prepare_prompt(
            template_name="risk_analysis",
            context=context,
        )
        
        if prompt_data is None:
            logger.error("template_not_found", template_name="risk_analysis")
            raise ValueError("Template 'risk_analysis' not found")
        
        return prompt_data

    def _calculate_streak_volatility(self, form: str) -> str:
        """Calculate streak volatility from form string."""
        if not form or len(form) < 2:
            return "Insufficient data"
        
        # Count pattern changes (W->L, L->W, etc.)
        changes = sum(1 for i in range(len(form) - 1) if form[i] != form[i + 1])
        volatility_ratio = changes / len(form) if len(form) > 0 else 0.0
        
        if volatility_ratio > 0.6:
            return "High (unstable)"
        elif volatility_ratio > 0.3:
            return "Medium"
        else:
            return "Low (stable)"

    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        """
        Analyze betting risk factors and model uncertainty.
        
        Args:
            input_data: AgentInputDTO with risk-related data
            
        Returns:
            AgentOutputDTO with risk score and signals
            
        Raises:
            Exception: Re-raises LLM call failures
        """
        logger.debug(
            "analyzing_risk",
            event_id=str(input_data.event_id),
            lambda_home=input_data.bundle.poisson_event_features.lambda_home,
            lambda_away=input_data.bundle.poisson_event_features.lambda_away,
        )

        prompt = self.build_prompt(input_data)
        
        logger.debug("risk_prompt_built", template_name=prompt.get("template_name"))

        result: RiskSchema = await self._call_llm(
            prompt_data=prompt,
            schema=RiskSchema,
        )

        logger.debug(
            "risk_analysis_complete",
            event_id=str(input_data.event_id),
            score=result.score,
            signals_count=len(result.signals),
        )

        return AgentOutputDTO(
            agent_name=self.name,
            event_id=input_data.event_id,
            score=result.score,
            signals=result.signals,
            raw=result.model_dump(),
        )