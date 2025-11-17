"""
Prioritizer LLM client using OpenAI SDK + OpenRouter with Instructor validation.
"""
import time
import asyncio
from typing import List, Dict, Any, Optional
import structlog
from instructor import Mode
from openai import AsyncOpenAI, APIStatusError
import instructor
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.infrastructure.ai.config_loader import AIConfigLoader, RetryConfigDTO
from app.infrastructure.ai.clients.schemas import EventPriorityBatch, EventPriorityScore
from app.infrastructure.config.policy_loader import PolicyLoader

logger = structlog.get_logger()


class PrioritizerLLMClient:
    """
    LLM client for event prioritization using OpenAI SDK + OpenRouter.

    Uses Instructor for structured output validation.
    Supports fallback models and rate limiting.
    """

    def __init__(self, ai_config: AIConfigLoader, policy_loader: PolicyLoader):
        """
        Initialize prioritizer LLM client.

        Args:
            ai_config: AI configuration loader (for LLM retry config from models.yml)
            policy_loader: Policy loader for business logic configuration
        """
        self.ai_config = ai_config
        self.policy_loader = policy_loader
        config = ai_config.load_models_config()

        prioritizer_config = config.get("prioritizer")
        if not prioritizer_config:
            raise ValueError("prioritizer configuration not found in models.yml")
        
        self.provider = prioritizer_config.get("provider")
        if not self.provider:
            raise ValueError("provider not found in prioritizer configuration")
        
        self.model = prioritizer_config.get("model")
        if not self.model:
            raise ValueError("model not found in prioritizer configuration")
        
        self.fallback_models = prioritizer_config.get("fallback_models", [])
        
        self.timeout_ms = prioritizer_config.get("timeout_ms")
        if self.timeout_ms is None:
            raise ValueError("timeout_ms not found in prioritizer configuration")
        
        self.batch_size = prioritizer_config.get("batch_size")
        if self.batch_size is None:
            raise ValueError("batch_size not found in prioritizer configuration")
        
        self.rate_limit_qps = prioritizer_config.get("rate_limit_qps")
        if self.rate_limit_qps is None:
            raise ValueError("rate_limit_qps not found in prioritizer configuration")

        # Load retry configuration from models.yml (LLM retry config)
        self.retry: RetryConfigDTO = ai_config.get_retry_config()

        self.base_url = ai_config.get_base_url(self.provider)
        self.api_key = ai_config.get_api_key(self.provider)

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {self.provider}")
        
        if not self.base_url:
            raise ValueError(f"Base URL not found for provider: {self.provider}")

        self._openai_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout_ms / 1000.0,
            max_retries=0,  # Disable SDK auto-retries, use manual retry logic
            default_headers={
                "X-OpenRouter-App-ID": "sports-oraculum",
                "X-Title": "Layerbit-Oraculum-Prioritizer"
            },
        )

        self._instructor_client = instructor.from_openai(self._openai_client, Mode.JSON)

        self._last_request_time = 0.0
        self._rate_limit_delay = 1.0 / self.rate_limit_qps if self.rate_limit_qps > 0 else 0

        self._system_prompt = None
        self._instruction_prompt = None

        logger.info(
            "prioritizer_llm_client_initialized",
            provider=self.provider,
            model=self.model,
            fallback_models=self.fallback_models,
            batch_size=self.batch_size,
            rate_limit_qps=self.rate_limit_qps,
            timeout_ms=self.timeout_ms,
            retry_max_attempts=self.retry.max_attempts,
            retry_retriable_codes=self.retry.retriable_status_codes
        )

    def _load_prompts(self):
        """Load prompt bundle from YAML."""
        if self._system_prompt is None or self._instruction_prompt is None:
            bundle = self.ai_config.load_prompt_bundle("prioritizer")
            self._system_prompt = bundle.get("system", "")
            self._instruction_prompt = bundle.get("instruction", "")

    async def _apply_rate_limit(self):
        """Apply rate limiting delay."""
        if self._rate_limit_delay > 0:
            now = time.time()
            elapsed = now - self._last_request_time

            if elapsed < self._rate_limit_delay:
                delay = self._rate_limit_delay - elapsed
                logger.debug("rate_limit_delay", delay_sec=delay)
                await asyncio.sleep(delay)

            self._last_request_time = time.time()

    async def prioritize_events(
        self,
        events: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> List[EventPriorityScore]:
        """
        Prioritize events using LLM with function calling.

        Args:
            events: List of event dicts with at least 'id' and contextual data
            temperature: Override temperature (default from config)

        Returns:
            List of EventPriorityScore with validated scores
        """
        self._load_prompts()

        if not events:
            logger.warning("no_events_to_prioritize")
            return []

        all_results = []

        for i in range(0, len(events), self.batch_size):
            batch = events[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(events) + self.batch_size - 1) // self.batch_size

            logger.info(
                "prioritizing_batch",
                batch_num=batch_num,
                total_batches=total_batches,
                batch_size=len(batch)
            )

            try:
                batch_results = await self._prioritize_batch(batch, temperature)
                all_results.extend(batch_results)

            except Exception as e:
                logger.error(
                    "batch_prioritization_failed",
                    batch_num=batch_num,
                    error=str(e),
                    exc_info=True
                )
                continue

        logger.info(
            "prioritization_complete",
            total_events=len(events),
            prioritized=len(all_results)
        )

        return all_results

    def _build_messages(self, system: str, user: str) -> list[
        ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam]:
        return [
            ChatCompletionSystemMessageParam(role="system", content=system),
            ChatCompletionUserMessageParam(role="user", content=user),
        ]

    def _delay_for(self, status: int, attempt: int, headers: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate delay for retry based on status code and attempt number.

        Args:
            status: HTTP status code
            attempt: Current attempt number (1-indexed)
            headers: Response headers (for Retry-After, X-RateLimit-Reset)

        Returns:
            Delay in seconds
        """
        # Check special_delays first
        special_delay = self.retry.special_delays.get(str(status))
        
        # Check Retry-After or X-RateLimit-Reset headers
        header_delay = None
        if headers:
            retry_after = headers.get("retry-after") or headers.get("Retry-After")
            if retry_after:
                try:
                    header_delay = float(retry_after)
                except (ValueError, TypeError):
                    pass
            
            if header_delay is None:
                rate_limit_reset = headers.get("x-ratelimit-reset") or headers.get("X-RateLimit-Reset")
                if rate_limit_reset:
                    try:
                        reset_timestamp = float(rate_limit_reset)
                        current_time = time.time()
                        header_delay = max(0, reset_timestamp - current_time)
                    except (ValueError, TypeError):
                        pass
        
        # Use maximum of special_delay and header_delay if both exist
        delays = [d for d in [special_delay, header_delay] if d is not None]
        if delays:
            return float(max(delays))
        
        # Exponential backoff fallback
        delay = self.retry.base_delay_sec * (2 ** max(0, attempt - 1))
        return min(delay, self.retry.max_delay_sec)

    async def _prioritize_batch(
        self,
        batch: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> List[EventPriorityScore]:
        """
        Prioritize single batch with fallback support and config-based retry logic.

        Args:
            batch: Batch of events
            temperature: Override temperature

        Returns:
            List of validated priority scores
        """
        await self._apply_rate_limit()

        models_to_try = [self.model] + self.fallback_models
        last_error = None

        for model_idx, model in enumerate(models_to_try):
            # Retry loop for current model
            for attempt in range(self.retry.max_attempts):
                try:
                    start_time = time.time()

                    result = await self._call_llm(
                        batch, 
                        model, 
                        temperature,
                        attempt=attempt + 1,
                        max_attempts=self.retry.max_attempts,
                        total_models=len(models_to_try)
                    )

                    logger.info(
                        "prioritization_success",
                        model_used=model,
                        batch_size=len(batch),
                        results_count=len(result.events),
                        fallback_hit=model_idx > 0,
                        attempt=attempt + 1
                    )

                    return result.events

                except APIStatusError as e:
                    status = getattr(e, "status_code", None) or getattr(
                        getattr(e, "response", None), "status_code", None
                    )
                    response = getattr(e, "response", None)
                    headers = getattr(response, "headers", {}) or {} if response else {}

                    # Extract provider-specific error codes if available (OpenRouter)
                    provider_raw_code = None
                    provider_name = None
                    if response and hasattr(response, 'headers'):
                        provider_raw_code = headers.get("x-openrouter-error-code") or headers.get("X-OpenRouter-Error-Code")
                        provider_name = headers.get("x-openrouter-provider") or headers.get("X-OpenRouter-Provider")
                    
                    error_message_short = str(e)[:200]
                    
                    # Log HTTP/LLM request failure
                    logger.warning(
                        "llm_request_failed",
                        model=model,
                        attempt=attempt + 1,
                        max_attempts=self.retry.max_attempts,
                        status_code=status,
                        error_type=type(e).__name__,
                        error_message_short=error_message_short,
                        provider_raw_code=provider_raw_code,
                        provider_name=provider_name,
                    )

                    # Check if status is retriable
                    is_retriable = status in set(self.retry.retriable_status_codes)
                    
                    if not is_retriable:
                        # Non-retriable status: log and skip to next model
                        logger.warning(
                            "llm_bad_request_debug_TODO_remove",
                            model=model,
                            status=status,
                            detail=str(e)[:1000],
                            attempt=attempt + 1
                        )
                        last_error = e
                        break  # Skip to next model

                    # Retriable status codes
                    if is_retriable:
                        wait = self._delay_for(status, attempt=attempt + 1, headers=headers)
                        logger.warning(
                            "llm_rate_or_server_waiting",
                            model=model,
                            status=status,
                            wait_sec=wait,
                            attempt=attempt + 1,
                            max_attempts=self.retry.max_attempts
                        )

                        # If we have more attempts, wait and retry
                        if attempt + 1 < self.retry.max_attempts:
                            await asyncio.sleep(wait)
                            continue  # Retry current model

                        # Attempts exhausted for this model
                        last_error = e
                        logger.warning(
                            "prioritization_attempts_exhausted_for_model",
                            model=model,
                            status=status,
                            attempts=self.retry.max_attempts
                        )
                        break  # Move to next model

                except Exception as e:
                    last_error = e
                    error_message_short = str(e)[:200]
                    
                    # Log parsing/validation failure (function calling or other non-HTTP errors)
                    logger.warning(
                        "llm_parse_failed",
                        model=model,
                        attempt=attempt + 1,
                        error_type=type(e).__name__,
                        error_message_short=error_message_short,
                    )

                    logger.warning(
                        "prioritization_attempt_failed",
                        model=model,
                        attempt=attempt + 1,
                        error=str(e),
                        error_type=type(e).__name__
                    )

                    # For non-APIStatusError exceptions, try next model
                    break

            # If we exhausted all models, log and return empty
            if model_idx == len(models_to_try) - 1:
                logger.error(
                    "all_prioritization_attempts_failed",
                    models_tried=models_to_try,
                    error=str(last_error) if last_error else "Unknown error"
                )

        return []

    async def _call_llm(
        self,
        batch: List[Dict[str, Any]],
        model: str,
        temperature: Optional[float] = None,
        attempt: Optional[int] = None,
        max_attempts: Optional[int] = None,
        total_models: Optional[int] = None,
    ) -> EventPriorityBatch:
        """
        Call LLM with Instructor for structured output.

        Args:
            batch: Event batch
            model: Model to use
            temperature: Temperature override
            attempt: Current attempt number (1-indexed)
            max_attempts: Maximum number of attempts
            total_models: Total number of models to try

        Returns:
            Validated EventPriorityBatch
        """
        self._load_prompts()
        events_summary = self._format_events_for_prompt(batch)
        user_message = f"{self._instruction_prompt}\n\n{events_summary}"

        model_config = self.ai_config.get_model_config(self.provider, model)
        
        if temperature is not None:
            temp = temperature
        else:
            temp = model_config.get("temperature")
            if temp is None:
                raise ValueError(f"temperature not found in model configuration for {model}")
        
        max_tokens = model_config.get("max_output_tokens")
        if max_tokens is None:
            raise ValueError(f"max_output_tokens not found in model configuration for {model}")
        
        msg = self._build_messages(self._system_prompt, user_message)

        try:
            response = await self._instructor_client.chat.completions.create(
                model=model,
                response_model=EventPriorityBatch,
                messages=msg,
                temperature=temp,
                max_tokens=max_tokens,
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "llm_parse_failed",
                model=model,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _format_events_for_prompt(self, events: List[Dict[str, Any]]) -> str:
        """
        Format events for LLM prompt.

        Args:
            events: List of event dicts

        Returns:
            Formatted string for prompt
        """
        lines = ["Events to prioritize:\n"]

        for idx, event in enumerate(events, 1):
            event_id = event.get("id")
            sport = event.get("sport_key", "unknown")
            home = event.get("home_team", "")
            away = event.get("away_team", "")
            commence_time = event.get("commence_time", "")

            lines.append(
                f"{idx}. ID: {event_id} | Sport: {sport} | "
                f"{home} vs {away} | Time: {commence_time}"
            )

        return "\n".join(lines)

    async def close(self):
        """Close HTTP client."""
        if self._openai_client:
            await self._openai_client.close()
            logger.info("prioritizer_llm_client_closed")
