from abc import ABC, abstractmethod
from typing import Type, TypeVar
from uuid import UUID
from pydantic import BaseModel

from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO
from app.llm.router import LLMRouter
from app.prompts.processor import PromptProcessor

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
    model_id: str
    prompt_name: str

    def __init__(self, llm: LLMRouter, prompt_processor: PromptProcessor):
        self.llm = llm
        self.prompt_processor = prompt_processor

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

    def build_prompt(self, input_data: AgentInputDTO) -> dict:
        pass

    async def _call_llm(self, prompt_data: dict, schema: Type[T]) -> T:
        return await self.llm.generate(prompt_data=prompt_data, schema=schema, model_id=self.model_id)

    def _validate(self, schema_output) -> AgentOutputDTO:
        """Map schema → AgentOutputDTO"""
        raise NotImplementedError
