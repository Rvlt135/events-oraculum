from typing import Dict, List, Any, Literal, Tuple
from uuid import UUID
from pydantic import BaseModel
import structlog

from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO, MainAnalysisOutputDTO
from app.llm.router import LLMRouter
from app.prompts.processor import PromptProcessor

logger = structlog.get_logger()


class SummarySchema(BaseModel):
    """Schema for LLM-generated summary."""
    summary: str



class MainAnalysisAgent:
    """Aggregates outputs from multiple agents and generates final analysis."""
    
    name = "main_analysis"
    prompt_name = "main_analysis"

    def __init__(self, llm_router: LLMRouter, prompt_processor: PromptProcessor):
        self.llm = llm_router
        self.model_id = "openai/gpt-4o-mini"
        self.prompt_processor = prompt_processor

    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        """Not used for MainAnalysisAgent - use aggregate() instead."""
        raise NotImplementedError("MainAnalysisAgent uses aggregate() method, not analyze()")

    async def aggregate(
        self,
        agent_outputs: Dict[str, AgentOutputDTO],
        input_dto: AgentInputDTO,
    ) -> MainAnalysisOutputDTO:
        """
        Aggregate agent outputs and generate final analysis summary.
        
        Args:
            agent_outputs: Dictionary mapping agent names to their outputs
            input_dto: Original input data for the event
            
        Returns:
            MainAnalysisOutputDTO with aggregated score and summary
        """
        logger.debug(
            "aggregating_agent_outputs",
            event_id=str(input_dto.event_id),
            agents_count=len(agent_outputs),
        )

        # 1. Compute aggregated_score as mean of all non-None scores
        scores = [
            output.score
            for output in agent_outputs.values()
            if output.score is not None
        ]
        
        if scores:
            aggregated_score = sum(scores) / len(scores)
            logger.debug("aggregated_score_computed", score=aggregated_score, scores_count=len(scores))
        else:
            aggregated_score = 0.0
            logger.debug("no_scores_available", aggregated_score=aggregated_score)

        # 2. Derive decision from aggregated_score and agent signals
        decision, decision_team_id = self._derive_decision(
            aggregated_score=aggregated_score,
            input_dto=input_dto,
        )
        
        logger.debug(
            "decision_computed",
            event_id=str(input_dto.event_id),
            decision=decision,
            decision_team_id=decision_team_id,
            aggregated_score=aggregated_score,
        )

        # 3. Collect agent signals
        agent_signals = []
        for agent_name, output in agent_outputs.items():
            if output.signals:
                agent_signals.extend(output.signals)
        
        logger.debug("agent_signals_collected", signals_count=len(agent_signals))

        # 4. Generate summary using LLM
        prompt_data = self.build_summary_prompt(
            aggregated_score=aggregated_score,
            agent_signals=agent_signals,
            decision=decision,
            decision_team_id=decision_team_id,
            input_dto=input_dto,
        )
        
        logger.debug("summary_prompt_built", template_name=prompt_data.get("template_name"))
        
        summary_result: SummarySchema = await self.llm.generate(
            prompt_data=prompt_data,
            schema=SummarySchema,
            model_id=self.model_id,
        )
        
        logger.debug("summary_generated", summary_length=len(summary_result.summary))

        # 5. Return MainAnalysisOutputDTO
        return MainAnalysisOutputDTO(
            event_id=input_dto.event_id,
            competition_id=input_dto.competition_id,
            season=input_dto.season,
            match_date=input_dto.match_date,
            aggregated_score=aggregated_score,
            summary=summary_result.summary,
            decision=decision,
            decision_team_id=decision_team_id,
            agents_outputs=agent_outputs,
        )

    def build_summary_prompt(
        self,
        aggregated_score: float,
        agent_signals: List[str],
        decision: Literal["home_win", "draw", "away_win", "no_bet"],
        decision_team_id: UUID | None,
        input_dto: AgentInputDTO,
    ) -> Dict[str, Any]:
        """
        Build prompt for summary generation using PromptProcessor.
        
        Args:
            aggregated_score: Aggregated score from all agents
            agent_signals: List of signals from all agents
            input_dto: AgentInputDTO containing event information
            decision: Decision based on aggregated_score
            decision_team_id: ID of the team to bet on
        Returns:
            Dictionary with system_prompt, user_prompt, parameters, template_name, template_version
            
        Raises:
            ValueError: If template not found
        """
        # Convert agent_signals to newline-joined text
        agent_signals_text = "\n".join(f"- {signal}" for signal in agent_signals) if agent_signals else "No signals available"
        
        # Extract fields from input_dto
        event_id = input_dto.bundle.event_id
        competition_id = input_dto.competition_id
        season = input_dto.season
        
        # Build context dict matching template placeholders
        context = {
            "event_id": str(event_id),
            "competition_id": str(competition_id),
            "season": season,
            "aggregated_score": aggregated_score,
            "agent_signals_text": agent_signals_text,
            "decision": decision,
            "decision_team_id": str(decision_team_id),
        }
        
        logger.debug(
            "building_summary_prompt",
            event_id=str(event_id),
            competition_id=str(competition_id),
            season=season,
            aggregated_score=aggregated_score,
            signals_count=len(agent_signals),
        )
        
        prompt_data = self.prompt_processor.prepare_prompt(
            template_name="main_analysis",
            context=context,
        )
        
        if prompt_data is None:
            logger.error("template_not_found", template_name="main_analysis")
            raise ValueError("Template 'main_analysis' not found")
        
        return prompt_data

    def _derive_decision(
        self,
        aggregated_score: float,
        input_dto: AgentInputDTO,
    ) -> Tuple[Literal["home_win", "draw", "away_win", "no_bet"], UUID | None]:
        """
        Derive decision from aggregated_score and agent signals.
        
        Args:
            aggregated_score: Aggregated score from all agents
            input_dto: AgentInputDTO containing event information
            
        Returns:
            Tuple of (decision, decision_team_id)
        """
        # Confidence threshold - if absolute score is below this, use "no_bet"
        CONFIDENCE_THRESHOLD = 0.1
        
        # Absolute value of score represents confidence
        confidence = abs(aggregated_score)
        
        # If confidence is too low, return "no_bet"
        if confidence < CONFIDENCE_THRESHOLD:
            return ("no_bet", None)
        
        # Determine outcome based on score sign
        if aggregated_score > 0:
            # Positive score favors home team
            decision: Literal["home_win", "draw", "away_win", "no_bet"] = "home_win"
            decision_team_id = input_dto.bundle.home_team.team_id
        elif aggregated_score < 0:
            # Negative score favors away team
            decision = "away_win"
            decision_team_id = input_dto.bundle.away_team.team_id
        else:
            # Score is exactly 0, treat as draw
            decision = "draw"
            decision_team_id = None
        
        return decision, decision_team_id