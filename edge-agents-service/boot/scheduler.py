import structlog
from app.tasks.broker import scheduler

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)


def main() -> None:
    scheduler.run()


if __name__ == "__main__":
    main()
