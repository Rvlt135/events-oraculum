"""
Infrastructure lifecycle management.
"""
import structlog

from app.infra.db.engine import dispose_engine, create_engine
from app.infra.rdb.client import initialize_redis, dispose_redis

logger = structlog.get_logger()


async def initialize() -> None:
    """Initialize all infrastructure resources."""
    logger.info("initializing_infrastructure")
    
    # Initialize database engine
    create_engine()
    
    # Initialize Redis
    await initialize_redis()
    
    logger.info("infrastructure_initialized")


async def dispose() -> None:
    """Dispose all infrastructure resources."""
    logger.info("disposing_infrastructure")
    
    # Dispose Redis
    await dispose_redis()
    
    # Dispose database engine
    await dispose_engine()
    
    logger.info("infrastructure_disposed")
