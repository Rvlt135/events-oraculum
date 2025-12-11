from typing import List, Dict, Any
from pydantic import BaseModel
import structlog

from app.agents.base import BaseAgent
from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO

logger = structlog.get_logger()


class TrendSchema(BaseModel):
    """Schema for trend analysis output."""
    score: float  # in range [-1, 1]
    signals: List[str]


class TrendAgent(BaseAgent):
    """Analyzes team form trends and recent performance patterns."""
    
    name = "trend_agent"
    model_id = "openai/gpt-4o-mini"
    prompt_name = "trend_analysis"

    def build_prompt(self, input_data: AgentInputDTO) -> Dict[str, Any]:
        """
        Build prompt for trend analysis using PromptProcessor.
        
        Args:
            input_data: AgentInputDTO containing match history data
            
        Returns:
            Dictionary with system_prompt, user_prompt, parameters, template_name, template_version
            
        Raises:
            ValueError: If template not found or prompt generation fails
        """
        bundle = input_data.bundle
        home_history = bundle.match_history_home
        away_history = bundle.match_history_away

        # Calculate trend indicators
        home_trend = self._calculate_trend(home_history)
        away_trend = self._calculate_trend(away_history)
        
        # Build context dict matching template placeholders
        context = {
            "home_matches_count": home_history.last_matches_count,
            "home_form": home_history.form_last_n,
            "home_goals_for": home_history.goals_for_last_n,
            "home_goals_against": home_history.goals_against_last_n,
            "home_wins": home_history.wins_last_n,
            "home_draws": home_history.draws_last_n,
            "home_losses": home_history.losses_last_n,
            "home_trend": home_trend,
            "away_matches_count": away_history.last_matches_count,
            "away_form": away_history.form_last_n,
            "away_goals_for": away_history.goals_for_last_n,
            "away_goals_against": away_history.goals_against_last_n,
            "away_wins": away_history.wins_last_n,
            "away_draws": away_history.draws_last_n,
            "away_losses": away_history.losses_last_n,
            "away_trend": away_trend,
        }
        
        logger.debug(
            "building_trend_prompt",
            event_id=str(input_data.event_id),
            home_matches_count=home_history.last_matches_count,
            away_matches_count=away_history.last_matches_count,
        )
        
        prompt_data = self.prompt_processor.prepare_prompt(
            template_name="trend_analysis",
            context=context,
        )
        
        if prompt_data is None:
            logger.error("template_not_found", template_name="trend_analysis")
            raise ValueError("Template 'trend_analysis' not found or prompt generation failed")
        
        return prompt_data

    def _calculate_trend(self, history) -> str:
        """Calculate trend indicator from match history."""
        if history.last_matches_count == 0:
            return "No data"
        
        # Simple trend: compare first half vs second half of form string
        form = history.form_last_n
        if len(form) < 2:
            return "Insufficient data"
        
        mid = len(form) // 2
        first_half = form[:mid]
        second_half = form[mid:]
        
        first_points = first_half.count('W') * 3 + first_half.count('D')
        second_points = second_half.count('W') * 3 + second_half.count('D')
        
        if second_points > first_points:
            return "Positive (improving)"
        elif second_points < first_points:
            return "Negative (degrading)"
        else:
            return "Stable"

    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        """
        Analyze team trends and form patterns.
        
        Args:
            input_data: AgentInputDTO with match history data
            
        Returns:
            AgentOutputDTO with trend score and signals
            
        Raises:
            Exception: Propagates LLM call failures
        """
        logger.debug(
            "analyzing_trends",
            event_id=str(input_data.event_id),
            home_matches=input_data.bundle.match_history_home.last_matches_count,
            away_matches=input_data.bundle.match_history_away.last_matches_count,
        )

        prompt = self.build_prompt(input_data)
        
        logger.debug("trend_prompt_built", template_name=prompt.get("template_name"))

        llm_result: TrendSchema = await self._call_llm(
            prompt_data=prompt,
            schema=TrendSchema,
        )

        logger.debug(
            "trend_analysis_complete",
            event_id=str(input_data.event_id),
            score=llm_result.score,
            signals_count=len(llm_result.signals),
        )

        return AgentOutputDTO(
            agent_name=self.name,
            event_id=input_data.event_id,
            score=llm_result.score,
            signals=llm_result.signals,
            raw=llm_result.model_dump(),
        )