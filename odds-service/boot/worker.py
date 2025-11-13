import asyncio
import structlog

from app.tasks.broker import broker
# from app.tasks.collector import collect_odds_task, collect_sports_task
from app.tasks import collector

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


async def main() -> None:
    logger.info("starting_taskiq_worker")

    # Container will be created automatically in broker.on_event(TaskiqEvents.WORKER_STARTUP)
    await broker.startup()
    logger.info("worker_started")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting_down_worker")
        await broker.shutdown()
        # Container disposal is handled automatically in broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)


if __name__ == "__main__":
    asyncio.run(main())
