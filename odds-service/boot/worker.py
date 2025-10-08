import asyncio
import structlog

from app.tasks.broker import broker

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


async def main() -> None:
    logger.info("starting_taskiq_worker")
    await broker.startup()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting_down_worker")
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
