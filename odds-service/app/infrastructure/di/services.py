"""
DI for sports services (for tasks and non-request contexts).
"""
from typing import TYPE_CHECKING

from app.services.sports_service import SportsService
from app.infrastructure.cache.sports import SportsCache
from app.tasks.broker import broker

if TYPE_CHECKING:
    from app.infrastructure.di.container import Container


async def get_sports_service() -> SportsService:
    """
    Get SportsService with injected dependencies from container.
    
    This function is used in tasks and other non-request contexts.
    For FastAPI request handlers, use app.api.dependencies.get_sports_service.
    
    Returns a service instance that manages its own session lifecycle.
    The service will create short-lived sessions per method call.
    """
    # Get container from broker.state (TaskIQ worker context)
    if not hasattr(broker, 'state') or not hasattr(broker.state, 'container'):
        raise RuntimeError(
            "Container not found in broker.state. "
            "Make sure worker/scheduler initialized container before running tasks."
        )
    
    container: "Container" = broker.state.container
    
    return SportsService(
        odds_client=container.odds_client,
        session_factory=container.session_factory,
        sports_cache=SportsCache(container.redis),
    )
