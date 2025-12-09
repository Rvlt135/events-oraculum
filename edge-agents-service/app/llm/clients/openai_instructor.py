from typing import Type, TypeVar, Any
from pydantic import BaseModel
from openai import AsyncOpenAI
import instructor
import structlog

from app.config.settings import settings
from app.config.model_loader import ModelConfig
from app.llm.clients.base import BaseLLMClient

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class OpenAIInstructorClient(BaseLLMClient):
    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            max_retries=settings.openrouter_max_retries,
            default_headers={
                "HTTP-Referer": settings.openrouter_referer,
                "X-Title": settings.openrouter_app_title,
            },
            timeout=settings.llm_timeout,
        )

        self.instructor_client = instructor.from_openai(self.client)

        logger.info(
            "openai_instructor_client_initialized",
            model=model_config.model_id,
            supports_json=model_config.supports_json_mode,
        )

    async def generate(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any
    ) -> T:
        temperature = kwargs.get("temperature", self.model_config.temperature_default)
        max_tokens = kwargs.get("max_tokens", self.model_config.max_tokens_default)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info(
            "generating_with_instructor",
            model=self.model_config.model_id,
            schema=schema.__name__,
            temperature=temperature,
        )

        try:
            if self.model_config.supports_json_mode:
                response = await self.instructor_client.chat.completions.create(
                    model=self.model_config.model_id,
                    messages=messages,
                    response_model=schema,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            else:
                response = await self.instructor_client.chat.completions.create(
                    model=self.model_config.model_id,
                    messages=messages,
                    response_model=schema,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            logger.info(
                "generation_successful",
                model=self.model_config.model_id,
                schema=schema.__name__,
            )

            return response

        except Exception as e:
            logger.error(
                "generation_failed",
                model=self.model_config.model_id,
                error=str(e),
            )
            raise

    def get_model_id(self) -> str:
        return self.model_config.model_id

    def supports_json_mode(self) -> bool:
        return self.model_config.supports_json_mode
