import asyncio
import structlog
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.infra.di.lifecycle import initialize as initialize_infrastructure, dispose as dispose_infrastructure
from app.tasks.broker import broker
from app.config import settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


async def main() -> None:
    logger.info("starting_taskiq_scheduler", schedules=settings.schedule_crons)

    # Initialize shared infrastructure
    await initialize_infrastructure()

    scheduler = TaskiqScheduler(
        broker=broker,
        sources=[LabelScheduleSource(broker)],
    )

    await scheduler.startup()
    logger.info("scheduler_started")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting_down_scheduler")
        await scheduler.shutdown()
        await dispose_infrastructure()


if __name__ == "__main__":
    asyncio.run(main())
