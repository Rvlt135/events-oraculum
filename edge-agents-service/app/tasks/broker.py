from taskiq import TaskiqScheduler
from taskiq_redis import ListQueueBroker, RedisScheduleSource
import structlog

from app.config.settings import settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

broker = ListQueueBroker(settings.redis_url).with_result_backend(
    result_backend=ListQueueBroker(settings.redis_url)
)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[RedisScheduleSource(settings.redis_url)],
)
