from app.config.settings import settings
from app.application import create_app

app = create_app(settings.environment)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=True,
    )
