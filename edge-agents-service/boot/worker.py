import structlog
from app.tasks.broker import broker

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)


def main() -> None:
    broker.run_worker()


if __name__ == "__main__":
    main()
