# app/agents/market_agent.py
from pydantic import BaseModel
import structlog

from app.agents.base import BaseAgent
from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO
from app.llm.llm_router import LLMRouter
from app.prompts.processor import PromptProcessor

logger = structlog.get_logger()


class MarketReasoningSchema(BaseModel):
    score: float
    signals: list[str]


class MarketAgent(BaseAgent):
    name = "market"
    model_id = "openai/gpt-4o-mini"
    prompt_name = "market_analysis"

    def __init__(self, llm: LLMRouter, prompt_processor: PromptProcessor):
        super().__init__(llm, prompt_processor)

    def build_prompt(self, input_data: AgentInputDTO) -> dict:
        """
        Build prompt using PromptProcessor with market analysis template.
        
        Args:
            input_data: AgentInputDTO containing bundle and edge data
            
        Returns:
            Dictionary with system_prompt, user_prompt, parameters, template_name, template_version
        """
        b = input_data.bundle
        e = input_data.edge
        
        context = {
            "fair_home": b.poisson_output.fair_home,
            "fair_away": b.poisson_output.fair_away,
            "market_home": b.market_odds.home_best,
            "market_away": b.market_odds.away_best,
            "edge_home": e.edge_home,
            "edge_draw": e.edge_draw,
            "edge_away": e.edge_away,
        }
        
        logger.debug(
            "building_prompt",
            prompt_name=self.prompt_name,
            event_id=str(input_data.event_id),
        )
        
        prompt_data = self.prompt_processor.prepare_prompt(
            template_name="market_analysis",
            context=context,
        )
        
        if prompt_data is None:
            logger.error("template_not_found", template_name="market_analysis")
            raise ValueError(f"Template 'market_analysis' not found")
        
        return prompt_data

    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        prompt = self.build_prompt(input_data)
        llm_result: MarketReasoningSchema = await self._call_llm(
            prompt_data=prompt,
            schema=MarketReasoningSchema,
        )

        return AgentOutputDTO(
            agent_name=self.name,
            event_id=input_data.event_id,
            score=llm_result.score,
            signals=llm_result.signals,
            raw=llm_result.model_dump(),
        )
