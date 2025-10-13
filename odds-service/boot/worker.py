import asyncio
import structlog

from app.infra.providers import infrastructure
from app.tasks.broker import broker
from app.tasks.collector import collect_odds_task

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
    await infrastructure.initialize()

    await broker.startup()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting_down_worker")
        await broker.shutdown()
        await infrastructure.dispose()


if __name__ == "__main__":
    asyncio.run(main())
