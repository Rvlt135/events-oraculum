"""
LLM service for AI-powered analysis and insights.

This service handles:
- LLM client lifecycle management
- Prompt loading and templating
- Retry logic for LLM requests
- Business logic for AI features
"""
from typing import Dict, Any, Optional, List
import structlog
import asyncio
import random

from app.infrastructure.ai.config_loader import AIConfigLoader
from app.infrastructure.ai.clients.base import (
    BaseLLMClient,
    LLMRequest,
    LLMResponse,
    LLMMessage,
)

logger = structlog.get_logger()


class LLMService:
    """Service for LLM operations."""

    def __init__(
        self,
        ai_config: AIConfigLoader,
        llm_client: Optional[BaseLLMClient] = None,
    ):
        """
        Initialize LLM service.

        Args:
            ai_config: AI configuration loader
            llm_client: Optional LLM client (for dependency injection)
        """
        self.ai_config = ai_config
        self._llm_client = llm_client
        self._retry_config = ai_config.get_retry_config()

        logger.info(
            "llm_service_initialized",
            has_client=llm_client is not None,
            retry_max_attempts=self._retry_config.max_attempts
        )

    @property
    def llm_client(self) -> BaseLLMClient:
        """
        Get LLM client (lazy initialization).

        Returns:
            BaseLLMClient instance
        """
        if self._llm_client is None:
            raise RuntimeError(
                "LLM client not initialized. "
                "Provide llm_client in constructor or initialize via DI."
            )
        return self._llm_client

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        retry: bool = True,
    ) -> LLMResponse:
        """
        Send completion request to LLM with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override temperature
            max_tokens: Override max tokens
            model: Override model
            retry: Enable retry on failures

        Returns:
            LLM response
        """
        llm_messages = [LLMMessage(**msg) for msg in messages]

        request = LLMRequest(
            messages=llm_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )

        if not retry:
            return await self.llm_client.complete(request)

        return await self._complete_with_retry(request)

    async def _complete_with_retry(self, request: LLMRequest) -> LLMResponse:
        """
        Execute LLM request with retry logic.

        Args:
            request: LLM request

        Returns:
            LLM response
        """
        max_attempts = self._retry_config.max_attempts
        base_delay = self._retry_config.base_delay_sec
        max_delay = self._retry_config.max_delay_sec
        retriable_codes = self._retry_config.retriable_status_codes

        last_error = None

        for attempt in range(max_attempts):
            try:
                logger.debug(
                    "llm_request_attempt",
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    model=request.model or self.llm_client.model
                )

                response = await self.llm_client.complete(request)

                logger.info(
                    "llm_request_success",
                    attempt=attempt + 1,
                    model=response.model,
                    provider=response.provider,
                    usage=response.usage
                )

                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    "llm_request_failed",
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    error=str(e),
                    error_type=type(e).__name__
                )

                if attempt < max_attempts - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter

                    logger.info("llm_retry_delay", delay_sec=total_delay, attempt=attempt + 1)
                    await asyncio.sleep(total_delay)

        logger.error(
            "llm_request_failed_all_attempts",
            max_attempts=max_attempts,
            error=str(last_error)
        )
        raise last_error

    async def complete_with_system_prompt(
        self,
        user_message: str,
        system_prompt_name: str = "system_default",
        system_prompt_override: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Send completion with system prompt.

        Args:
            user_message: User message content
            system_prompt_name: Name of system prompt to load
            system_prompt_override: Override system prompt instead of loading
            **kwargs: Additional arguments for complete()

        Returns:
            LLM response
        """
        if system_prompt_override:
            system_content = system_prompt_override
        else:
            system_content = self.ai_config.load_prompt(system_prompt_name)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message},
        ]

        return await self.complete(messages, **kwargs)

    async def complete_with_template(
        self,
        template_name: str,
        template_vars: Dict[str, Any],
        system_prompt_name: str = "system_default",
        **kwargs,
    ) -> LLMResponse:
        """
        Send completion using prompt template.

        Args:
            template_name: Name of prompt template
            template_vars: Variables to format template
            system_prompt_name: Name of system prompt
            **kwargs: Additional arguments for complete()

        Returns:
            LLM response
        """
        template = self.ai_config.load_prompt(template_name)
        user_message = template.format(**template_vars)

        return await self.complete_with_system_prompt(
            user_message=user_message,
            system_prompt_name=system_prompt_name,
            **kwargs
        )

    def get_available_prompts(self) -> List[str]:
        """
        List available prompt templates.

        Returns:
            List of prompt names
        """
        return self.ai_config.list_available_prompts()

    async def close(self):
        """Close LLM client and cleanup resources."""
        if self._llm_client:
            await self._llm_client.close()
            logger.info("llm_service_closed")
