import uvicorn

from services.odds_service.config import get_odds_service_config


def main() -> None:
    config = get_odds_service_config()

    uvicorn.run(
        "services.odds_service.api.app:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
