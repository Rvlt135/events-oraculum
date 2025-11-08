from app.application import create_app
from app.config.settings import settings
import uvicorn

app = create_app(settings.environment)


if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
