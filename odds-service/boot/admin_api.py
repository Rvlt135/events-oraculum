import uvicorn
import structlog

from app.config import settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)


def main() -> None:
    uvicorn.run(
        "app.admin_api.app:app",
        host=settings.admin_api_host,
        port=settings.admin_api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
