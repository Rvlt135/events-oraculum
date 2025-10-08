from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import structlog

from app.config.settings import settings
from app.cache.redis import redis_cache
from app.routes import insights, stats
from app.observability.logging import configure_logging

configure_logging()

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_gateway_service")
    await redis_cache.connect()
    yield
    await redis_cache.disconnect()
    logger.info("shutting_down_gateway_service")


app = FastAPI(
    title="Gateway Service",
    description="Public API for betting insights and recommendations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router)
app.include_router(stats.router)


@app.get("/")
async def root() -> dict:
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
