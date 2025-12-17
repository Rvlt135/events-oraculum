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
    
    # Final production agent weights (fixed, deterministic)
    _AGENT_WEIGHTS: Dict[str, float] = {
        "math_agent": 1.0,
        "trend_agent": 1.0,
        "risk_agent": 0.7,
        "market": 0.5,  # market_agent uses name "market"
        "meta_agent": 0.0,
    }
    _DEFAULT_WEIGHT: float = 1.0

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
        
        Normalizes agent scores by clamping to [-1, 1] range and applying
        per-agent weight caps before aggregation to ensure balanced contribution.
        
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

        # 1. Normalize, weight, and aggregate agent scores
        weighted_scores = self._collect_weighted_scores(agent_outputs)
        aggregated_score = self._aggregate_scores(weighted_scores)

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
        
        Aligns wording strength in summary with aggregated_score magnitude
        through explicit interpretation rules in the prompt template.
        
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
        
        # Determine score bucket for logging
        abs_score = abs(aggregated_score)
        if abs_score < 0.4:
            score_bucket = "low"
        elif abs_score < 0.7:
            score_bucket = "moderate"
        else:
            score_bucket = "high"
        
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
            score_bucket=score_bucket,
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
        Derive decision from aggregated_score with production thresholds.
        
        Args:
            aggregated_score: Aggregated score from all agents
            input_dto: AgentInputDTO containing event information
            
        Returns:
            Tuple of (decision, decision_team_id)
        """
        abs_score: float = abs(aggregated_score)
        
        # Decision thresholds (production, fixed)
        if abs_score < 0.1:
            # Very low confidence → no_bet
            return ("no_bet", None)
        elif abs_score < 0.2:
            # Low confidence → draw / high uncertainty
            return ("draw", None)
        
        # Higher confidence → home_win or away_win by sign
        if aggregated_score > 0:
            decision: Literal["home_win", "draw", "away_win", "no_bet"] = "home_win"
            decision_team_id = input_dto.bundle.home_team.team_id
        else:
            decision = "away_win"
            decision_team_id = input_dto.bundle.away_team.team_id
        
        return decision, decision_team_id

    def _normalize_agent_score(self, raw_score: float) -> float:
        """
        Clamp agent score to [-1.0, 1.0] range.
        
        Args:
            raw_score: Raw score from the agent
            
        Returns:
            Clamped score in [-1.0, 1.0] range
        """
        return max(-1.0, min(1.0, raw_score))

    def _apply_agent_weight(self, agent_name: str, normalized_score: float) -> float:
        """
        Apply agent weight multiplicatively to normalized score.
        
        Enforces invariants:
        - market_agent cannot outweigh math_agent
        - meta_agent cannot increase confidence (weight = 0.0)
        
        Args:
            agent_name: Name of the agent
            normalized_score: Normalized score in [-1.0, 1.0] range
            
        Returns:
            Weighted score
        """
        weight: float = self._AGENT_WEIGHTS.get(agent_name, self._DEFAULT_WEIGHT)
        weighted_score: float = normalized_score * weight
        
        return weighted_score

    def _collect_weighted_scores(
        self,
        agent_outputs: Dict[str, AgentOutputDTO],
    ) -> List[float]:
        """
        Collect, normalize, and weight scores from all agents.
        
        Args:
            agent_outputs: Dictionary mapping agent names to their outputs
            
        Returns:
            List of weighted scores ready for aggregation
        """
        weighted_scores: List[float] = []
        
        for agent_name, output in agent_outputs.items():
            if output.score is None:
                continue
            
            raw_score: float = output.score
            
            # Step 1: Normalize (clamp to [-1.0, 1.0])
            normalized_score: float = self._normalize_agent_score(raw_score)
            
            logger.debug(
                "agent_score_normalized",
                agent_name=agent_name,
                raw_score=raw_score,
                normalized_score=normalized_score,
            )
            
            # Step 2: Apply weight
            weighted_score: float = self._apply_agent_weight(agent_name, normalized_score)
            weighted_scores.append(weighted_score)
            
            weight: float = self._AGENT_WEIGHTS.get(agent_name, self._DEFAULT_WEIGHT)
            
            logger.debug(
                "agent_weight_applied",
                agent_name=agent_name,
                normalized_score=normalized_score,
                weighted_score=weighted_score,
                weight=weight,
            )
        
        return weighted_scores

    def _aggregate_scores(self, weighted_scores: List[float]) -> float:
        """
        Aggregate weighted scores into final aggregated score.
        
        Computes mean of weighted scores. If no valid scores, returns 0.0.
        
        Args:
            weighted_scores: List of weighted scores from all agents
            
        Returns:
            Aggregated score (mean of weighted scores, or 0.0 if empty)
        """
        if not weighted_scores:
            aggregated_score: float = 0.0
            logger.debug("no_scores_available", aggregated_score=aggregated_score)
            return aggregated_score
        
        aggregated_score: float = sum(weighted_scores) / len(weighted_scores)
        logger.debug(
            "aggregated_score_computed",
            agents_count=len(weighted_scores),
            aggregated_score=aggregated_score,
        )
        
        return aggregated_score