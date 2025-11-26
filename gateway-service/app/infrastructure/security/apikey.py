from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key:
        logger.warning("api_key_missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing",
        )

    if api_key != settings.api_key:
        logger.warning("api_key_invalid", provided_key=api_key[:8] + "...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )

    logger.debug("api_key_verified")
    return api_key

