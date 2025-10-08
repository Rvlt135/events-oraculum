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
        **kwargs: Any
    ) -> T:
        pass

    @abstractmethod
    def get_model_id(self) -> str:
        pass

    @abstractmethod
    def supports_json_mode(self) -> bool:
        pass
