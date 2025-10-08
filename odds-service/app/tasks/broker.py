from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker
from app.config import settings

redis_backend = RedisAsyncResultBackend(settings.redis_url)
broker = ListQueueBroker(url=settings.redis_url).with_result_backend(redis_backend)
