import asyncio
import structlog

from app.infra.di.lifecycle import initialize as initialize_infrastructure, dispose as dispose_infrastructure
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

    # Initialize shared infrastructure
    await initialize_infrastructure()

    await broker.startup()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting_down_worker")
        await broker.shutdown()
        await dispose_infrastructure()


if __name__ == "__main__":
    asyncio.run(main())
