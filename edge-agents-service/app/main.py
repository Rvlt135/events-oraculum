from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config.settings import settings
from app.db.pg import init_db, engine
from app.cache.redis import recommendation_cache
from app.routes import health, run, recommendations, internal

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_edge_agents_service")
    await init_db()
    await recommendation_cache.initialize()
    yield
    await recommendation_cache.dispose()
    await engine.dispose()
    logger.info("shutting_down_edge_agents_service")


def create_app(env: str = "development") -> FastAPI:
    app = FastAPI(
        title="Edge Agents Service",
        description="AI agents for betting event analysis",
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

    app.include_router(health.router)
    app.include_router(run.router)
    app.include_router(recommendations.router)
    app.include_router(internal.router)

    @app.get("/")
    async def root() -> dict:
        return {
            "service": settings.service_name,
            "version": "0.1.0",
            "status": "running",
            "environment": env,
        }

    return app


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
