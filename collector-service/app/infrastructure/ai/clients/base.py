"""
Base LLM client interface and common types.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class LLMMessage(BaseModel):
    """Message in LLM conversation."""
    role: str
    content: str


class LLMRequest(BaseModel):
    """Request to LLM."""
    messages: List[LLMMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = {}


class LLMResponse(BaseModel):
    """Response from LLM."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = {}
    metadata: Dict[str, Any] = {}


class BaseLLMClient(ABC):
    """Base interface for LLM clients."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Initialize LLM client.

        Args:
            provider: Provider name (e.g., 'openai')
            model: Model name (e.g., 'gpt-4o-mini')
            api_key: API key for provider
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        logger.info(
            "llm_client_initialized",
            provider=provider,
            model=model,
            has_api_key=bool(api_key),
            timeout=timeout
        )

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Send completion request to LLM.

        Args:
            request: LLM request with messages and parameters

        Returns:
            LLM response with generated content
        """
        pass

    @abstractmethod
    async def close(self):
        """Close client and cleanup resources."""
        pass
