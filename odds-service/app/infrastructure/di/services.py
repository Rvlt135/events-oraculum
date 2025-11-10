"""
DI for services (for tasks and non-request contexts).

This module provides factory functions for creating services from Container.
Services are primarily used in worker/scheduler context, not FastAPI.
"""
from typing import TYPE_CHECKING

from app.tasks.broker import broker

if TYPE_CHECKING:
    from app.services.sports_service import SportsService
    from app.services.events_service import EventsService
    from app.infrastructure.di.container import Container


async def get_sports_service() -> "SportsService":
    """
    Get SportsService with injected dependencies from container.

    This function is used in tasks and other non-request contexts (worker/scheduler).
    For FastAPI request handlers, use app.api.dependencies.get_sports_service.

    Both functions use the same underlying logic via container.create_sports_service(),
    ensuring consistency across different contexts.

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
    return container.create_sports_service()


async def get_events_service() -> "EventsService":
    """
    Get EventsService with injected dependencies from container.

    This function is used in tasks and other non-request contexts (worker/scheduler).
    For FastAPI request handlers, use app.api.dependencies.get_events_service.

    Both functions use the same underlying logic via container.create_events_service(),
    ensuring consistency across different contexts.

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
    return container.create_events_service()
