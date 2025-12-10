from typing import Type, TypeVar, Any
from pydantic import BaseModel
import structlog

from app.config.model_loader import ModelConfig
from app.llm.base import BaseLLMClient

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class LangChainClient(BaseLLMClient):
    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

        logger.info(
            "langchain_client_initialized",
            model=model_config.model_id,
            note="Adapter stub - LangChain integration can be implemented here"
        )

    async def generate(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any
    ) -> T:
        logger.warning(
            "langchain_generation_not_implemented",
            model=self.model_config.model_id,
            note="Use instructor client or implement LangChain integration"
        )

        raise NotImplementedError(
            "LangChain client is a stub. "
            "To implement: use langchain-openai ChatOpenAI with "
            "structured output via with_structured_output(schema)"
        )

    def get_model_id(self) -> str:
        return self.model_config.model_id

    def supports_json_mode(self) -> bool:
        return self.model_config.supports_json_mode
