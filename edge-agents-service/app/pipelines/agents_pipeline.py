import asyncio
import asyncio

import structlog

from app.agents.base import BaseAgent
from app.agents.main_analysis_agent import MainAnalysisAgent
from app.domain.entities.agents.dto import AgentOutputDTO, AgentInputDTO, MainAnalysisOutputDTO

logger = structlog.get_logger()

class AgentsPipeline:
    def __init__(self, agents: list[BaseAgent], main_agent: MainAnalysisAgent):
        self.agents = agents
        self.main_agent = main_agent

    async def run_for_input(self, input_dto: AgentInputDTO) -> dict[str, AgentOutputDTO]:
        tasks = [
            self._run_anlyse_agent(agent, input_dto)
            for agent in self.agents
        ]
        results = await asyncio.gather(*tasks)

        # Превратить list в dict
        return {res.agent_name: res for res in results}

    async def run_final(self, agent_outputs: dict[str, AgentOutputDTO], input_dto: AgentInputDTO) -> MainAnalysisOutputDTO:
        return await self.main_agent.aggregate(agent_outputs, input_dto)

    async def _run_anlyse_agent(self, agent: BaseAgent, input_dto):
        return await agent.analyze(input_dto)