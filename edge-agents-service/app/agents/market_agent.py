# app/agents/market_agent.py
from typing import Type
from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO

class MarketReasoningSchema(BaseModel):
    score: float
    signals: list[str]


class MarketAgent(BaseAgent):
    name = "market"

    def _build_prompt(self, input_data: AgentInputDTO) -> str:
        b = input_data.bundle
        e = input_data.edge
        return (
            "You are a betting market analyst.\n"
            f"Poisson fair_home={b.poisson_output.fair_home}, fair_away={b.poisson_output.fair_away}\n"
            f"Market home={b.market_odds.home_best}, away={b.market_odds.away_best}\n"
            f"Edge home={e.edge_home}, draw={e.edge_draw}, away={e.edge_away}\n"
            "Return a confidence score in range [-1,1] and key reasoning bullets."
        )

    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        prompt = self._build_prompt(input_data)
        llm_result: MarketReasoningSchema = await self._call_llm(
            prompt=prompt,
            schema=MarketReasoningSchema,
        )

        return AgentOutputDTO(
            agent_name=self.name,
            event_id=input_data.event_id,
            score=llm_result.score,
            signals=llm_result.signals,
            raw=llm_result.model_dump(),
        )
