from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config.settings import settings
from app.infrastructure.cache.redis import redis_cache_manager
from app.infrastructure.db.engine import engine
from app.infrastructure.db.orm import Base
from app.observability.logging import configure_logging
from app.api.routes import auth, base, insights, stats
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
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "endpoint") and hasattr(route, "methods"):
                endpoint = route.endpoint
                if inspect.iscoroutinefunction(endpoint) or inspect.isfunction(endpoint):
                    sig = inspect.signature(endpoint)
                    # Check if endpoint uses get_current_user in its dependencies
                    uses_auth = False
                    for param_name, param in sig.parameters.items():
                        if hasattr(param.default, "dependency"):
                            if param.default.dependency == get_current_user:
                                uses_auth = True
                                break
                    
                    if uses_auth:
                        # Find the operation in OpenAPI schema
                        path = route.path
                        if path in openapi_schema.get("paths", {}):
                            path_item = openapi_schema["paths"][path]
                            # Check all HTTP methods for this route
                            for method in route.methods:
                                method_lower = method.lower()
                                if method_lower in path_item:
                                    operation = path_item[method_lower]
                                    if "security" not in operation:
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
    app.include_router(base.router)
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

