from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from sqlalchemy import text

import redis.asyncio as redis
from app.config.settings import settings
from app.infrastructure.cache.redis import RedisCache
from app.infrastructure.db.engine import engine
from app.infrastructure.db.orm import Base
from app.utils.logging import configure_logging
from app.api.routes import auth, insights, stats
from fastapi.openapi.utils import get_openapi
from app.api.di.auth_deps import get_current_user
import inspect
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

configure_logging()

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_gateway_service")
    # TODO: update in future use multiple cache databases
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis_client = redis_client
    app.state.redis_cache = RedisCache(redis_client, ttl=settings.cache_ttl_seconds)

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    yield
    await redis_client.close()
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
                    if "/health" in path or "/metrics" in path or "/v1/stats/summary" in path:
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
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app

