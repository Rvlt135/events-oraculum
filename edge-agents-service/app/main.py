from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config.settings import settings
from app.infrastructure.db.pg import init_db, engine
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, CollectorRegistry

from app.api.routes import agent_analyze, internal
from app.api.routes import health, run
from fastapi.openapi.utils import get_openapi

from app.infrastructure.di.container import create_container, dispose_container

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        route_type = "admin" if request.url.path.startswith(settings.admin_prefix) else "public"
        # стараемся брать шаблон маршрута (/items/{id}) вместо фактического пути
        path_label = getattr(request.scope.get("route"), "path", request.url.path)

        request.app.state.http_requests_total.labels(
            method=request.method,
            path=path_label,
            route_type=route_type
        ).inc()

        return await call_next(request)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    Creates dependencies and stores them in app.state.container.
    """
    # logger.info("starting_odds_service", admin_enabled=settings.admin_enabled)

    # Create container
    container = create_container()

    # Store container in app state
    app.state.container = container

    # Metrics
    registry = CollectorRegistry()
    http_requests_total = Counter(
        "edge_agents_service_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "route_type"],
        registry=registry,
    )
    app.state.metrics_registry = registry
    app.state.http_requests_total = http_requests_total

    yield

    # Dispose container
    await dispose_container(container)

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
    app.include_router(agent_analyze.router)
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
