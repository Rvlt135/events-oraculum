from typing import Dict, List
from uuid import UUID
from pydantic import BaseModel
import structlog

from app.agents.base import BaseAgent
from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO, MainAnalysisOutputDTO
from app.llm.llm_router import LLMRouter

logger = structlog.get_logger()


class SummarySchema(BaseModel):
    """Schema for LLM-generated summary."""
    summary: str


class MainAnalysisAgent:
    """Aggregates outputs from multiple agents and generates final analysis."""
    
    name = "main_analysis"

    def __init__(self, llm_router: LLMRouter):
        self.llm = llm_router

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

        # 2. Collect agent signals
        agent_signals = []
        for agent_name, output in agent_outputs.items():
            if output.signals:
                agent_signals.extend(output.signals)
        
        logger.debug("agent_signals_collected", signals_count=len(agent_signals))

        # 3. Generate summary using LLM
        prompt = self._build_summary_prompt(
            event_id=input_dto.event_id,
            competition_id=input_dto.competition_id,
            season=input_dto.season,
            aggregated_score=aggregated_score,
            agent_signals=agent_signals,
        )
        
        logger.debug("summary_prompt_built", prompt_length=len(prompt))
        
        summary_result: SummarySchema = await self.llm.generate(
            prompt=prompt,
            schema=SummarySchema,
        )
        
        logger.debug("summary_generated", summary_length=len(summary_result.summary))

        # 4. Return MainAnalysisOutputDTO
        return MainAnalysisOutputDTO(
            event_id=input_dto.event_id,
            competition_id=input_dto.competition_id,
            season=input_dto.season,
            match_date=input_dto.match_date,
            aggregated_score=aggregated_score,
            summary=summary_result.summary,
            agents_outputs=agent_outputs,
        )

    def _build_summary_prompt(
        self,
        event_id: UUID,
        competition_id: UUID,
        season: int,
        aggregated_score: float,
        agent_signals: List[str],
    ) -> str:
        """Build prompt for summary generation."""
        signals_text = "\n".join(f"- {signal}" for signal in agent_signals) if agent_signals else "No signals available"
        
        return (
            f"Generate a concise natural-language summary for a betting event analysis.\n\n"
            f"Event ID: {event_id}\n"
            f"Competition ID: {competition_id}\n"
            f"Season: {season}\n"
            f"Aggregated Score: {aggregated_score:.3f}\n\n"
            f"Agent Signals:\n{signals_text}\n\n"
            f"Provide a brief summary (2-3 sentences) of the analysis findings."
        )