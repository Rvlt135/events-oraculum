from typing import Any

from taskiq import TaskiqEvents
from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker
from app.config import settings
from app.infra.di.lifecycle import initialize as initialize_infrastructure, dispose as dispose_infrastructure

redis_backend = RedisAsyncResultBackend(settings.redis_url)
broker = ListQueueBroker(url=settings.redis_url).with_result_backend(redis_backend)

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_broker_startup(state: Any):
    await initialize_infrastructure()

@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_broker_shutdown(state: Any):
    await dispose_infrastructure()