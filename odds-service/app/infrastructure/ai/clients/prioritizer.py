"""
Prioritizer LLM client using OpenAI SDK + OpenRouter with Instructor validation.
"""
import time
import asyncio
from typing import List, Dict, Any, Optional
import structlog
from openai import AsyncOpenAI
import instructor

from app.infrastructure.ai.config_loader import AIConfigLoader
from app.infrastructure.ai.clients.schemas import EventPriorityBatch, EventPriorityScore

logger = structlog.get_logger()


class PrioritizerLLMClient:
    """
    LLM client for event prioritization using OpenAI SDK + OpenRouter.

    Uses Instructor for structured output validation.
    Supports fallback models and rate limiting.
    """

    def __init__(self, ai_config: AIConfigLoader):
        """
        Initialize prioritizer LLM client.

        Args:
            ai_config: AI configuration loader
        """
        self.ai_config = ai_config
        config = ai_config.load_models_config()

        prioritizer_config = config.get("prioritizer", {})
        self.provider = prioritizer_config.get("provider", "openrouter")
        self.model = prioritizer_config.get("model", "deepseek/deepseek-chat")
        self.fallback_models = prioritizer_config.get("fallback_models", [])
        self.timeout_ms = prioritizer_config.get("timeout_ms", 30000)
        self.batch_size = prioritizer_config.get("batch_size", 50)
        self.rate_limit_qps = prioritizer_config.get("rate_limit_qps", 5)

        provider_config = ai_config.get_provider_config(self.provider)
        self.base_url = provider_config.get("base_url")
        self.api_key = ai_config.get_api_key(self.provider)

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {self.provider}")

        self._openai_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout_ms / 1000.0,
        )

        self._instructor_client = instructor.from_openai(self._openai_client)

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
            timeout_ms=self.timeout_ms
        )

    def _load_prompts(self):
        """Load system and instruction prompts."""
        if self._system_prompt is None:
            try:
                self._system_prompt = self.ai_config.load_prompt("prioritizer_system")
            except FileNotFoundError:
                logger.warning("prioritizer_system_prompt_not_found_using_default")
                self._system_prompt = "You are an AI assistant that prioritizes sports betting events."

        if self._instruction_prompt is None:
            try:
                self._instruction_prompt = self.ai_config.load_prompt("prioritizer_instruction")
            except FileNotFoundError:
                logger.warning("prioritizer_instruction_prompt_not_found_using_default")
                self._instruction_prompt = (
                    "Analyze the following events and assign priority scores (0.0 to 1.0) "
                    "based on betting value, data quality, and event importance."
                )

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
        Prioritize events using LLM with Instructor validation.

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

    async def _prioritize_batch(
        self,
        batch: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> List[EventPriorityScore]:
        """
        Prioritize single batch with fallback support.

        Args:
            batch: Batch of events
            temperature: Override temperature

        Returns:
            List of validated priority scores
        """
        await self._apply_rate_limit()

        models_to_try = [self.model] + self.fallback_models
        last_error = None

        for attempt, model in enumerate(models_to_try):
            try:
                logger.debug(
                    "attempting_prioritization",
                    model=model,
                    attempt=attempt + 1,
                    total_models=len(models_to_try),
                    batch_size=len(batch)
                )

                start_time = time.time()

                result = await self._call_llm(batch, model, temperature)

                duration_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    "prioritization_success",
                    model_used=model,
                    batch_size=len(batch),
                    results_count=len(result.events),
                    duration_ms=duration_ms,
                    fallback_hit=attempt > 0
                )

                return result.events

            except Exception as e:
                last_error = e
                logger.warning(
                    "prioritization_attempt_failed",
                    model=model,
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )

                if attempt < len(models_to_try) - 1:
                    logger.info("trying_fallback_model", next_model=models_to_try[attempt + 1])
                    await asyncio.sleep(1)

        logger.error(
            "all_prioritization_attempts_failed",
            models_tried=models_to_try,
            error=str(last_error)
        )

        return []

    async def _call_llm(
        self,
        batch: List[Dict[str, Any]],
        model: str,
        temperature: Optional[float] = None,
    ) -> EventPriorityBatch:
        """
        Call LLM with Instructor for structured output.

        Args:
            batch: Event batch
            model: Model to use
            temperature: Temperature override

        Returns:
            Validated EventPriorityBatch
        """
        events_summary = self._format_events_for_prompt(batch)

        user_message = f"{self._instruction_prompt}\n\n{events_summary}"

        model_config = self.ai_config.get_model_config(self.provider, model)
        temp = temperature if temperature is not None else model_config.get("temperature", 0.3)

        response = await self._instructor_client.chat.completions.create(
            model=model,
            response_model=EventPriorityBatch,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=temp,
            max_tokens=model_config.get("max_output_tokens", 4096),
        )

        return response

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
