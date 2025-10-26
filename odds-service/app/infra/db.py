"""
DEPRECATED: This module is deprecated. Use app.infra.providers instead.

All database infrastructure is now managed through the unified
InfrastructureProvider in app.infra.providers.

This file is kept for backward compatibility during migration.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()


# Import from new location for backward compatibility
from app.infra.providers import infrastructure, get_db_session

# Alias for backward compatibility
db_manager = infrastructure

logger.warning(
    "deprecated_module",
    module="app.infra.db",
    message="Use app.infra.providers instead"
)
