from typing import List
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

    def _build_prompt(self, input_data: AgentInputDTO) -> str:
        """
        Build prompt for trend analysis.
        
        Args:
            input_data: AgentInputDTO containing match history data
            
        Returns:
            Formatted prompt string with team form and trend indicators
        """
        bundle = input_data.bundle
        home_history = bundle.match_history_home
        away_history = bundle.match_history_away

        # Calculate trend indicators
        home_trend = self._calculate_trend(home_history)
        away_trend = self._calculate_trend(away_history)

        prompt = (
            "You are a football form and trend analyst. Analyze recent team performance trends.\n\n"
            f"HOME TEAM:\n"
            f"Recent form (last {home_history.last_matches_count} matches): {home_history.form_last_n}\n"
            f"Goals for (last {home_history.last_matches_count}): {home_history.goals_for_last_n}\n"
            f"Goals against (last {home_history.last_matches_count}): {home_history.goals_against_last_n}\n"
            f"Wins: {home_history.wins_last_n}, Draws: {home_history.draws_last_n}, Losses: {home_history.losses_last_n}\n"
            f"Trend: {home_trend}\n\n"
            f"AWAY TEAM:\n"
            f"Recent form (last {away_history.last_matches_count} matches): {away_history.form_last_n}\n"
            f"Goals for (last {away_history.last_matches_count}): {away_history.goals_for_last_n}\n"
            f"Goals against (last {away_history.last_matches_count}): {away_history.goals_against_last_n}\n"
            f"Wins: {away_history.wins_last_n}, Draws: {away_history.draws_last_n}, Losses: {away_history.losses_last_n}\n"
            f"Trend: {away_trend}\n\n"
            "Analyze the trends:\n"
            "- Positive trend = improving results (more recent wins, better goal difference)\n"
            "- Negative trend = degrading results (more recent losses, worse goal difference)\n"
            "Return a confidence score in range [-1, 1] where:\n"
            "- Positive values indicate home team has better trend\n"
            "- Negative values indicate away team has better trend\n"
            "Include key reasoning signals as bullet points."
        )
        
        return prompt

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

        prompt = self._build_prompt(input_data)
        
        logger.debug("trend_prompt_built", prompt_length=len(prompt))

        llm_result: TrendSchema = await self._call_llm(
            prompt=prompt,
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