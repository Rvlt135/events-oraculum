import asyncio
import structlog
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.tasks.broker import broker
from app.config import settings
# Import tasks module to ensure tasks are registered with broker
from app.tasks import collector  # noqa: F401
from app.tasks import prioritizer  # noqa: F401

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


async def main() -> None:
    logger.info("starting_taskiq_scheduler")

    label_source = LabelScheduleSource(broker)
    scheduler = TaskiqScheduler(
        broker=broker,
        sources=[label_source],
    )

    await scheduler.startup()
    logger.info("scheduler_started")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting_down_scheduler")
        await scheduler.shutdown()
        # Container disposal is handled automatically in broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)


if __name__ == "__main__":
    asyncio.run(main())
