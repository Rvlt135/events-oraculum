from typing import Any
import structlog
from taskiq import TaskiqEvents
from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker

from app.config import settings
from app.infrastructure.di.container import create_container, dispose_container

logger = structlog.get_logger()

redis_backend = RedisAsyncResultBackend(settings.redis_url)
broker = ListQueueBroker(url=settings.redis_url).with_result_backend(redis_backend)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_broker_startup(state: Any) -> None:
    """
    Initialize container when worker starts.
    
    This is called when TaskIQ worker starts (both via boot/worker.py and taskiq worker command).
    """
    logger.info("initializing_container_in_worker")
    
    # Create container and store in broker state
    container = create_container()
    broker.state.container = container
    
    logger.info("container_initialized_in_worker")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_broker_shutdown(state: Any) -> None:
    """
    Dispose container when worker shuts down.
    
    This is called when TaskIQ worker shuts down.
    """
    logger.info("disposing_container_in_worker")
    
    if hasattr(broker.state, 'container') and broker.state.container:
        await dispose_container(broker.state.container)
        broker.state.container = None
    
    logger.info("container_disposed_in_worker")