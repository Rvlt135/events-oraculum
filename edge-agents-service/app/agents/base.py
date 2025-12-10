from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, TypeVar
from uuid import UUID
from pydantic import BaseModel

from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO
from app.llm.llm_router import LLMRouter
T = TypeVar("T", bound=BaseModel)

class AgentPrediction(BaseModel):
    event_id: UUID
    pick: str
    confidence: float
    explanation: str
    reasoning: str
    model_version: str


class BaseAgent(ABC):
    name: str = "base"
    model_id: str = "openai/gpt-4o-mini"

    def __init__(self, llm: LLMRouter):
        self.llm = llm

    # @abstractmethod
    # async def analyze(self, event_features: Dict[str, Any]) -> Optional[AgentPrediction]:
    #     pass
    #
    # @abstractmethod
    # def get_model_version(self) -> str:
    #     pass

    @abstractmethod
    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        """
        Main entry point for each agent.
        Args:
            input_data: AgentInputDTO
        Returns:
            AgentOutputDTO
        """
        pass

    def _build_prompt(self, input_data: AgentInputDTO) -> str:
        raise NotImplementedError

    async def _call_llm(self, prompt: str, schema: Type[T]) -> T:
        return await self.llm.generate(prompt=prompt, schema=schema)

    def _validate(self, schema_output) -> AgentOutputDTO:
        """Map schema → AgentOutputDTO"""
        raise NotImplementedError
