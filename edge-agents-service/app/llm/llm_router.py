import asyncio
import time
import structlog
from typing import Type, Any, TypeVar
from pydantic import BaseModel

from app.llm.base import BaseLLMClient

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)

class LLMRouter:
    def __init__(self, clients: dict[str, BaseLLMClient], default_model: str):
        self.clients = clients
        self.default_model = default_model

    async def generate(
        self,
        prompt: dict,
        schema: Type[T],
        model_id: str | None = None,
    ) -> T:
        """
        Generate structured output from prompt using LLM client.
        
        Args:
            prompt: User prompt text
            schema: Pydantic schema type for structured output
            model_id: Optional model identifier to route to
            
        Returns:
            Validated BaseModel instance matching schema
        """
        client = self._select_client_if_needed(model_id)
        
        payload = self._prepare_request(prompt, schema)
        payload = self._apply_json_mode(payload, client)
        model_id = client.get_model_id()

        logger.debug(
            "request_initiated", prompt_size=len(prompt), model_id=model_id
        )
        
        raw = None
        latency = 0.0
        for attempt in range(3):
            try:
                start = time.monotonic()
                raw = await client.generate(
                    schema=payload["schema"],
                    prompt=payload["prompt"],
                    json_mode=payload.get("json_mode", False),
                )
                latency = time.monotonic() - start
                break
            except Exception as e:
                if attempt == 2:
                    logger.error("generation_failed", error=str(e), error_type=type(e).__name__)
                await asyncio.sleep(0.5 * (2**attempt))
        
        result: T = schema.model_validate(raw)

        logger.debug("response_received", tokens=getattr(raw, "tokens", None), latency=latency)
        
        return result

    def _select_client_if_needed(self, model_id: str | None) -> BaseLLMClient:
        """
        Select client based on model_id or use default.
        
        Args:
            model_id: Optional model identifier to route to
            
        Returns:
            BaseLLMClient instance (selected or default client)
        """
        if model_id is None:
            logger.debug("using_default_client", model_id=None, default_model=self.default_model)
            return self.clients[self.default_model]
        
        if model_id in self.clients:
            logger.debug("client_found", model_id=model_id)
            return self.clients[model_id]
        
        logger.warning(
            "llm_model_not_found",
            model_id=model_id,
            fallback=self.default_model,
        )
        return self.clients[self.default_model]

    def select_client(self, model_id: str) -> BaseLLMClient:
        """
        Select client by matching ModelConfig.model_id.
        
        Args:
            model_id: Model identifier (e.g., "openai/gpt-4o-mini")
            
        Returns:
            BaseLLMClient instance (matched client or default fallback)
        """
        logger.debug("selecting_client", model_id=model_id)
        
        for client in self.clients.values():
            if client.model_config.model_id == model_id:
                logger.debug("client_matched", model_id=model_id)
                return client
        
        logger.warning(
            "llm_model_not_found",
            model_id=model_id,
            fallback=self.default_model,
        )
        return self.clients[self.default_model]

    def _prepare_request(
        self, prompt: dict, schema: Type[BaseModel]
    ) -> dict[str, Any]:
        """
        Prepare request payload with prompt and schema.
        
        Args:
            prompt: User prompt text
            schema: Pydantic schema type for structured output
            
        Returns:
            Request payload dictionary
        """
        payload = {"prompt": prompt, "schema": schema}
        logger.debug("request_prepared", prompt_length=len(prompt))
        return payload

    def _apply_json_mode(
        self, payload: dict[str, Any], client: BaseLLMClient
    ) -> dict[str, Any]:
        """
        Apply JSON mode flag if client supports it.
        
        Args:
            payload: Request payload dictionary
            client: LLM client instance to check
            
        Returns:
            Updated payload (with json_mode if supported)
        """
        if client.supports_json_mode():
            payload = payload.copy()
            payload["json_mode"] = True
            logger.debug("json_mode_enabled", json_mode=True)
        return payload
