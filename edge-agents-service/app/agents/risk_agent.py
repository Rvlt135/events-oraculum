from typing import List
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

    def _build_prompt(self, input_data: AgentInputDTO) -> str:
        """
        Build prompt for risk analysis.
        
        Args:
            input_data: AgentInputDTO containing risk-related data
            
        Returns:
            Formatted prompt string with risk indicators
        """
        bundle = input_data.bundle
        edge = input_data.edge
        
        # Poisson variance indicators
        poisson = bundle.poisson_event_features
        lambda_home = poisson.lambda_home
        lambda_away = poisson.lambda_away
        lambda_diff = abs(lambda_home - lambda_away)
        lambda_volatility = abs(lambda_home - lambda_away) / max(lambda_home, lambda_away) if max(lambda_home, lambda_away) > 0 else 0.0
        
        # Elo uncertainty factor
        elo = bundle.elo_output
        elo_uncertainty = abs(elo.expected_home - elo.expected_away)
        
        # Market odds gaps
        market = bundle.market_odds
        home_gap = abs(market.home_best - market.home_avg) if market.home_avg > 0 else 0.0
        away_gap = abs(market.away_best - market.away_avg) if market.away_avg > 0 else 0.0
        draw_gap = abs(market.draw_best - market.draw_avg) if market.draw_best and market.draw_avg else 0.0
        
        # Edge percentages
        edge_home = edge.edge_home
        edge_away = edge.edge_away
        edge_draw = edge.edge_draw
        negative_edges = sum(1 for e in [edge_home, edge_away, edge_draw] if e < 0)
        
        # Match history streak volatility
        home_form = bundle.match_history_home.form_last_n
        away_form = bundle.match_history_away.form_last_n
        home_volatility = self._calculate_streak_volatility(home_form)
        away_volatility = self._calculate_streak_volatility(away_form)

        prompt = (
            "You are a betting risk analyst. Evaluate risk factors and model uncertainty.\n\n"
            "POISSON VARIANCE INDICATORS:\n"
            f"λ_home: {lambda_home:.3f}\n"
            f"λ_away: {lambda_away:.3f}\n"
            f"λ_difference: {lambda_diff:.3f}\n"
            f"λ_volatility: {lambda_volatility:.3f}\n\n"
            "ELO UNCERTAINTY:\n"
            f"expected_home: {elo.expected_home:.3f}\n"
            f"expected_away: {elo.expected_away:.3f}\n"
            f"uncertainty_factor: {elo_uncertainty:.3f}\n\n"
            "MARKET ODDS GAPS (big deviation → high risk):\n"
            f"Home gap (best vs avg): {home_gap:.3f}\n"
            f"Away gap (best vs avg): {away_gap:.3f}\n"
            f"Draw gap (best vs avg): {draw_gap:.3f}\n\n"
            "EDGE PERCENTAGES (negative or unstable → high risk):\n"
            f"edge_home: {edge_home:.2f}%\n"
            f"edge_away: {edge_away:.2f}%\n"
            f"edge_draw: {edge_draw:.2f}%\n"
            f"negative_edges_count: {negative_edges}\n\n"
            "MATCH HISTORY STREAK VOLATILITY:\n"
            f"Home form: {home_form} (volatility: {home_volatility})\n"
            f"Away form: {away_form} (volatility: {away_volatility})\n\n"
            "Analyze risk factors:\n"
            "- High volatility in Poisson/Elo → high risk\n"
            "- Large market odds gaps → high risk\n"
            "- Negative edges → high risk\n"
            "- Unstable form streaks → high risk\n"
            "Return a score in range [-1, 1] where:\n"
            "- Negative values = high risk (uncertain, volatile, negative edge)\n"
            "- Positive values = low risk (stable, consistent, positive edge)\n"
            "Include key risk signals as bullet points."
        )
        
        return prompt

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

        prompt = self._build_prompt(input_data)
        
        logger.debug("risk_prompt_built", prompt_length=len(prompt))

        result: RiskSchema = await self._call_llm(
            prompt=prompt,
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