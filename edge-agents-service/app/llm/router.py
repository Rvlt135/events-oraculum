import asyncio
import time
import structlog
from typing import Type, Any, TypeVar, Optional
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
        prompt_data: dict,
        schema: Type[T],
        model_id: Optional[str] = None,
    ) -> T:
        """
        Generate structured output from prompt using LLM client.
        
        Args:
            prompt_data: Dictionary with system_prompt, user_prompt, parameters
            schema: Pydantic schema type for structured output
            model_id: Optional model identifier to route to
            
        Returns:
            Validated BaseModel instance matching schema
        """
        # 1. Extract structured prompt fields
        try:
            system_prompt = prompt_data["system_prompt"]
            user_prompt = prompt_data["user_prompt"]
            parameters = prompt_data.get("parameters", {})
        except KeyError as e:
            raise ValueError(f"invalid_prompt_data: missing required field '{e}'")
        
        # 2. Select model backend
        client = self._select_client_if_needed(model_id)
        selected_model_id = client.get_model_id()
        logger.debug("model_selected", model_id=selected_model_id)
        
        # 3. Build payload dictionary
        payload = {
            "system_prompt": system_prompt,
            "prompt": user_prompt,
            **parameters,
        }
        
        # 4. Apply JSON-mode
        payload = self._apply_json_mode(payload, client)
        
        # 5. Execute LLM call with retries
        raw = None
        latency = 0.0
        for attempt in range(3):
            try:
                start = time.monotonic()
                raw = await client.generate(
                    schema=schema,
                    prompt=payload["prompt"],
                    system_prompt=payload["system_prompt"],
                    json_mode=payload.get("json_mode", False),
                    temperature=payload.get("temperature"),
                    max_tokens=payload.get("max_tokens"),
                    top_p=payload.get("top_p"),
                )
                latency = time.monotonic() - start
                break
            except Exception as e:
                logger.debug("retry_attempt", attempt=attempt + 1, error=str(e))
                if attempt == 2:
                    logger.error("generation_failed", error=str(e), error_type=type(e).__name__)
                    raise
                await asyncio.sleep(0.5 * (2**attempt))
        
        # 6. Measure latency and log it
        logger.debug("response_received", latency=latency, tokens=getattr(raw, "tokens", None))
        
        # 7. Validate output using provided schema
        try:
            raw_json = raw.model_dump_json()
            result: T = schema.model_validate_json(raw_json)
        except Exception as e:
            logger.error("schema_validation_failed", error=str(e))
            raise ValueError("schema_validation_failed")
        
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
