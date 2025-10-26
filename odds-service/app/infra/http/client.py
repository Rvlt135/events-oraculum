"""
Base HTTP client for common HTTP operations.
"""
from typing import Any
import httpx
from aiolimiter import AsyncLimiter
import structlog

logger = structlog.get_logger()


def _merge_dicts(base: dict, override: dict | None) -> dict:
    """Merge two dicts, with override taking precedence."""
    if override is None:
        return base.copy()
    result = base.copy()
    result.update(override)
    return result


class BaseHttpClient:
    """
    Reusable base HTTP client with rate limiting and common GET operations.
    
    Provides:
    - Configured httpx.AsyncClient with timeout
    - Rate limiting via AsyncLimiter
    - URL building with base_url
    - JSON response parsing with error handling
    """
    
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        limiter: AsyncLimiter | None = None,
        client: httpx.AsyncClient | None = None,
        default_params: dict[str, Any] | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        # Create or use provided client
        self._client = client or httpx.AsyncClient(timeout=timeout)
        
        # Create or use provided limiter
        self.limiter = limiter or AsyncLimiter(max_rate=10, time_period=60)
        
        # Store default params/headers
        self._default_params = default_params or {}
        self._default_headers = default_headers or {}
    
    def build_url(self, path: str) -> str:
        """
        Build full URL by joining base_url and path.
        
        Handles trailing/leading slashes to avoid duplicate slashes.
        """
        path = path.lstrip("/")
        return f"{self.base_url}/{path}"
    
    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """
        Perform GET request and return parsed JSON.
        
        - Respects rate limiter
        - Merges default_params with request params
        - Raises httpx.HTTPStatusError on non-2xx responses
        - Returns raw JSON (dict/list)
        
        Args:
            path: URL path relative to base_url
            params: Query parameters (merged with default_params)
            
        Returns:
            Parsed JSON response
        """
        url = self.build_url(path)
        merged_params = _merge_dicts(self._default_params, params)
        
        async with self.limiter:
            response = await self._client.get(url, params=merged_params)
            response.raise_for_status()
            return response.json()
    
    async def aclose(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.aclose()
        return False
