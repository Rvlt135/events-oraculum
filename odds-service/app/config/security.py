from typing import Optional
import structlog

from fastapi import HTTPException, Header
from app.config.settings import settings

logger = structlog.get_logger()

async def verify_admin_token(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
) -> None:
    """
    Simple token-based admin authentication.

    If ADMIN_TOKEN is configured, validates the token from header.
    For production, use network-level security (IP allowlist, mTLS, auth proxy).
    """
    if settings.admin_token:
        if not x_admin_token or x_admin_token != settings.admin_token:
            logger.warning("admin_unauthorized_attempt", provided_token_exists=bool(x_admin_token))
            raise HTTPException(status_code=401, detail="Unauthorized")