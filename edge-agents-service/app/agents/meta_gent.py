from typing import List, Dict, Any
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
    model_id = "openai/gpt-4o-mini"
    prompt_name = "meta_analysis"

    def build_prompt(self, input_data: AgentInputDTO) -> Dict[str, Any]:
        """
        Build prompt using PromptProcessor with meta analysis template.
        
        Args:
            input_data: AgentInputDTO containing model outputs and features
            
        Returns:
            Dictionary with system_prompt, user_prompt, parameters, template_name, template_version
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
        
        # Build context dict matching template placeholders
        # Using simple objects for nested access in template
        class SimpleObj:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        context = {
            "poisson": SimpleObj(
                p_home=poisson.p_home or 0.0,
                p_draw=poisson.p_draw or 0.0,
                p_away=poisson.p_away or 0.0,
            ),
            "poisson_fair_home": poisson_fair_home,
            "poisson_fair_away": poisson_fair_away,
            "elo": SimpleObj(
                p_home=elo.p_home or 0.0,
                p_draw=elo.p_draw or 0.0,
                p_away=elo.p_away or 0.0,
                expected_home=elo.expected_home or 0.0,
                expected_away=elo.expected_away or 0.0,
            ),
            "market": SimpleObj(
                home_best=market.home_best,
                away_best=market.away_best,
            ),
            "market_home_mispricing": market_home_mispricing,
            "market_away_mispricing": market_away_mispricing,
            "edge": SimpleObj(
                edge_home=edge.edge_home,
                edge_away=edge.edge_away,
                edge_draw=edge.edge_draw,
            ),
            "home_form": home_form,
            "home_instability": home_instability,
            "away_form": away_form,
            "away_instability": away_instability,
            "poisson_favors_home": "home" if poisson_favors_home else "away",
            "elo_favors_home": "home" if elo_favors_home else "away",
            "conflict": "Yes" if conflict else "No",
            "prob_diff": prob_diff,
        }
        
        logger.info(
            "building_meta_prompt",
            prompt_name=self.prompt_name,
            event_id=str(input_data.event_id),
        )
        
        prompt_data = self.prompt_processor.prepare_prompt(
            template_name="meta_analysis",
            context=context,
        )
        
        if prompt_data is None:
            logger.warning(
                "template_not_found_or_invalid",
                template_name="meta_analysis",
                event_id=str(input_data.event_id),
            )
            return {}
        
        return prompt_data

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

        prompt = self.build_prompt(input_data)
        
        if not prompt:
            logger.error("meta_prompt_build_failed", event_id=str(input_data.event_id))
            raise ValueError("Failed to build meta prompt - template not found or invalid")
        
        logger.debug("meta_prompt_built", template_name=prompt.get("template_name"))

        result: MetaSchema = await self._call_llm(
            prompt_data=prompt,
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