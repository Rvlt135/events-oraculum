from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

from app.config.settings import settings
from app.infra.providers import infrastructure
from app.routes import public, admin

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

# Metrics
http_requests_total = Counter(
    "odds_service_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "route_type"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP requests by route type (public/admin)."""

    async def dispatch(self, request: Request, call_next):
        route_type = "admin" if request.url.path.startswith(settings.admin_prefix) else "public"
        http_requests_total.labels(
            method=request.method,
            path=request.url.path,
            route_type=route_type
        ).inc()
        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_odds_service", admin_enabled=settings.admin_enabled)

    await infrastructure.initialize()

    yield

    await infrastructure.dispose()

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
        reload=True,
    )
