import asyncio

from services.odds_service.tasks.scheduler import start_scheduler


def main() -> None:
    asyncio.run(start_scheduler())


if __name__ == "__main__":
    main()
