from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import structlog

from app.config.settings import settings
from app.infra.db import db_manager
from app.infra.redis_client import redis_manager

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_odds_service")

    await db_manager.initialize()
    await redis_manager.initialize()

    yield

    await redis_manager.dispose()
    await db_manager.dispose()

    logger.info("shutting_down_odds_service")


def create_app(env: str = "development") -> FastAPI:
    app = FastAPI(
        title="Odds Service",
        description="Sports odds collection and normalization service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict:
        return {
            "service": settings.service_name,
            "version": "0.1.0",
            "status": "running",
            "environment": env,
        }

    @app.get("/health")
    async def health() -> dict:
        return {"status": "healthy"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app(settings.environment)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8083,
        log_level=settings.log_level.lower(),
        reload=True,
    )
