import asyncio
import structlog

from app.tasks.broker import broker
# Import tasks modules to ensure they're registered with broker
from app.tasks import collector  # noqa: F401
from app.tasks import sync_teams  # noqa: F401
from app.tasks import prioritizer  # noqa: F401
from app.tasks import sync_teams # noqa: F401
from app.tasks import feature_layer  # noqa: F401
from app.tasks import models_layer  # noqa: F401
from app.tasks import event_layer  # noqa: F401

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
