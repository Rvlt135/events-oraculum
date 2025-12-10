from typing import List
from pydantic import BaseModel
import structlog

from app.agents.base import BaseAgent
from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO

logger = structlog.get_logger()


class MetaSchema(BaseModel):
    """Schema for meta-level analysis output."""
    score: float  # meta-confidence score in [-1, 1]
    signals: List[str]  # short reasoning bullets


class MetaAgent(BaseAgent):
    """Produces high-level consolidated insights from multiple model outputs."""
    
    name = "meta_agent"

    def _build_prompt(self, input_data: AgentInputDTO) -> str:
        """
        Build prompt for meta-level analysis.
        
        Args:
            input_data: AgentInputDTO containing model outputs and features
            
        Returns:
            Formatted prompt string with meta-level context
        """
        bundle = input_data.bundle
        edge = input_data.edge
        
        # Probabilistic outputs
        poisson = bundle.poisson_output
        elo = bundle.elo_output
        
        # Market mispricing indicators
        market = bundle.market_odds
        poisson_fair_home = poisson.fair_home if poisson.fair_home else 0.0
        poisson_fair_away = poisson.fair_away if poisson.fair_away else 0.0
        market_home_mispricing = abs(market.home_best - poisson_fair_home) if poisson_fair_home > 0 else 0.0
        market_away_mispricing = abs(market.away_best - poisson_fair_away) if poisson_fair_away > 0 else 0.0
        
        # Recent form and streak instability
        home_form = bundle.match_history_home.form_last_n
        away_form = bundle.match_history_away.form_last_n
        home_instability = self._calculate_instability(home_form)
        away_instability = self._calculate_instability(away_form)
        
        # Conflicting signals detection
        poisson_favors_home = (poisson.p_home or 0.0) > (poisson.p_away or 0.0)
        elo_favors_home = (elo.p_home or 0.0) > (elo.p_away or 0.0)
        conflict = poisson_favors_home != elo_favors_home
        
        # Deterministic vs probabilistic comparison
        poisson_home_prob = poisson.p_home if poisson.p_home else 0.0
        elo_home_prob = elo.p_home if elo.p_home else 0.0
        prob_diff = abs(poisson_home_prob - elo_home_prob)

        prompt = (
            "You are a meta-level betting analyst. Synthesize insights from multiple models.\n\n"
            "PROBABILISTIC OUTPUTS:\n"
            "Poisson Model:\n"
            f"  P(home)={poisson.p_home:.3f}, P(draw)={poisson.p_draw:.3f}, P(away)={poisson.p_away:.3f}\n"
            f"  Fair odds: home={poisson_fair_home:.2f}, away={poisson_fair_away:.2f}\n"
            "Elo Model:\n"
            f"  P(home)={elo.p_home:.3f}, P(draw)={elo.p_draw:.3f}, P(away)={elo.p_away:.3f}\n"
            f"  Expected: home={elo.expected_home:.3f}, away={elo.expected_away:.3f}\n\n"
            "MARKET MISPRICING INDICATORS:\n"
            f"Market odds: home={market.home_best:.2f}, away={market.away_best:.2f}\n"
            f"Poisson fair: home={poisson_fair_home:.2f}, away={poisson_fair_away:.2f}\n"
            f"Mispricing: home={market_home_mispricing:.2f}, away={market_away_mispricing:.2f}\n"
            f"Edge: home={edge.edge_home:.2f}%, away={edge.edge_away:.2f}%, draw={edge.edge_draw:.2f}%\n\n"
            "RECENT FORM + STREAK INSTABILITY:\n"
            f"Home form: {home_form} (instability: {home_instability})\n"
            f"Away form: {away_form} (instability: {away_instability})\n\n"
            "CONFLICTING SIGNALS:\n"
            f"Poisson favors: {'home' if poisson_favors_home else 'away'}\n"
            f"Elo favors: {'home' if elo_favors_home else 'away'}\n"
            f"Models conflict: {'Yes' if conflict else 'No'}\n"
            f"Probability difference: {prob_diff:.3f}\n\n"
            "Your goal: Produce a high-level consolidated insight, not a direct prediction.\n"
            "Consider:\n"
            "- Agreement/disagreement between models\n"
            "- Market efficiency vs model predictions\n"
            "- Form stability vs model confidence\n"
            "- Overall meta-confidence in the analysis\n"
            "Return a meta-confidence score in range [-1, 1] where:\n"
            "- Positive = high confidence in consolidated insight\n"
            "- Negative = low confidence, conflicting signals\n"
            "Include short reasoning bullets."
        )
        
        return prompt

    def _calculate_instability(self, form: str) -> str:
        """Calculate streak instability from form string."""
        if not form or len(form) < 2:
            return "Insufficient data"
        
        # Count pattern changes
        changes = sum(1 for i in range(len(form) - 1) if form[i] != form[i + 1])
        instability_ratio = changes / len(form) if len(form) > 0 else 0.0
        
        if instability_ratio > 0.6:
            return "High"
        elif instability_ratio > 0.3:
            return "Medium"
        else:
            return "Low"

    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        """
        Analyze meta-level context and produce consolidated insights.
        
        Args:
            input_data: AgentInputDTO with model outputs and features
            
        Returns:
            AgentOutputDTO with meta-confidence score and signals
            
        Raises:
            Exception: Re-raises LLM call failures
        """
        logger.debug(
            "analyzing_meta",
            event_id=str(input_data.event_id),
            poisson_home_prob=input_data.bundle.poisson_output.p_home,
            elo_home_prob=input_data.bundle.elo_output.p_home,
        )

        prompt = self._build_prompt(input_data)
        
        logger.debug("meta_prompt_built", prompt_length=len(prompt))

        result: MetaSchema = await self._call_llm(
            prompt=prompt,
            schema=MetaSchema,
        )

        logger.debug(
            "meta_analysis_complete",
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