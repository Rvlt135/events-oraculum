from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config.settings import settings
from app.infrastructure.db.pg import init_db, engine
from app.infrastructure.cache.redis import recommendation_cache
from app.api.routes import recommendations, internal
from app.api.routes import health, run
from fastapi.openapi.utils import get_openapi


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

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your JWT access token"
            }
        }

        # Automatically detect and add security to operations using get_current_user
        for path, path_item in openapi_schema["paths"].items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Skip public endpoints
                    if "/health" in path: # or "/metrics" in path or "/v1/stats/summary" in path
                        continue
                    # Add security requirement
                    operation["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

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
