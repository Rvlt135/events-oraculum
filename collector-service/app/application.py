from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, CollectorRegistry
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

from app.config.settings import settings
from app.api.routes import admin, public, tasks
from app.infrastructure.di.container import Container, create_container, dispose_container

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
    logger.info("starting_odds_service", admin_enabled=settings.admin_enabled)

    # Create container
    container = create_container()
    
    # Load policy loader
    if container.policy_loader:
        await container.policy_loader.load()
    
    # Store container in app state
    app.state.container = container

    # Metrics
    registry = CollectorRegistry()
    http_requests_total = Counter(
        "odds_service_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "route_type"],
        registry=registry,
    )
    app.state.metrics_registry = registry
    app.state.http_requests_total = http_requests_total

    yield

    # Dispose container
    await dispose_container(container)

    logger.info("shutting_down_odds_service")


def create_app(env: str = "development") -> FastAPI:
    """
    Create unified FastAPI application with public and admin routes.

    Admin routes are conditionally mounted based on ADMIN_ENABLED setting.
    """
    # Determine if admin docs should be included
    include_admin_in_schema = settings.admin_enabled and settings.admin_docs_enabled

    app = FastAPI(
        title="Odds Service",
        description="Sports odds collection and normalization service",
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )

    # Add middleware
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include public routes
    app.include_router(public.router)

    # Conditionally include admin routes
    if settings.admin_enabled:
        app.include_router(
            admin.router,
            prefix=settings.admin_prefix,
            include_in_schema=include_admin_in_schema,
        )
        app.include_router(
            tasks.router,
            prefix=settings.admin_prefix_tasks,
            include_in_schema=include_admin_in_schema,
        )
        logger.info(
            "admin_routes_enabled",
            prefix=settings.admin_prefix,
            docs_enabled=include_admin_in_schema
        )
    else:
        logger.info("admin_routes_disabled")

    # Prometheus metrics endpoint
    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        data = generate_latest(app.state.metrics_registry)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return app