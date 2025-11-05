from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import inspect
from app.security.auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import structlog

from app.config.settings import settings
from app.cache.redis import redis_cache_manager
from app.db.pg import engine
from app.routes import insights, stats, auth
from app.observability.logging import configure_logging
from app.domain.auth_models import Base

configure_logging()

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_gateway_service")
    await redis_cache_manager.initialize()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await redis_cache_manager.dispose()
    await engine.dispose()
    logger.info("shutting_down_gateway_service")


def create_app(env: str = "production") -> FastAPI:
    app = FastAPI(
        title="Gateway Service",
        description="Public API for betting insights and recommendations",
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
                    if "/health" in path or "/metrics" in path or "/v1/stats/summary'" in path:
                        continue
                    # Add security requirement
                    operation["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(insights.router)
    app.include_router(stats.router)

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
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
