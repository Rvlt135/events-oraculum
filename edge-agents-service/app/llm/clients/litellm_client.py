from typing import Type, TypeVar, Any
from pydantic import BaseModel
import structlog

from app.config.model_loader import ModelConfig
from app.llm.base import BaseLLMClient

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class LiteLLMClient(BaseLLMClient):
    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

        logger.info(
            "litellm_client_initialized",
            model=model_config.model_id,
            note="Adapter stub - LiteLLM integration can be implemented here"
        )

    async def generate(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any
    ) -> T:
        logger.warning(
            "litellm_generation_not_implemented",
            model=self.model_config.model_id,
            note="Use instructor client or implement LiteLLM integration"
        )

        raise NotImplementedError(
            "LiteLLM client is a stub. "
            "To implement: use litellm.acompletion() with "
            "response_format for structured output"
        )

    def get_model_id(self) -> str:
        return self.model_config.model_id

    def supports_json_mode(self) -> bool:
        return self.model_config.supports_json_mode
