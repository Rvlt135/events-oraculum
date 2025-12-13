from abc import ABC, abstractmethod
from typing import Type, TypeVar, Dict, Any
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):


    @abstractmethod
    async def generate(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: str = "",
        json_mode: bool | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ) -> T:
        """
        Args:
            schema: Pydantic model to validate the response
            prompt: Prompt to generate the response
            system_prompt: System prompt
            json_mode: JSON mode
            temperature: Temperature
            max_tokens: Max tokens
            top_p: Top-p
        """
        pass

    @abstractmethod
    def get_model_id(self) -> str:
        pass

    @abstractmethod
    def supports_json_mode(self) -> bool:
        pass
