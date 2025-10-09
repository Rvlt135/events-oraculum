"""
Public API routes for odds-service.

These routes provide read-only access to odds data and service information.
"""

from fastapi import APIRouter
from prometheus_client import Counter
import structlog

from app.config.settings import settings
from app.domain.schemas import ServiceInfoResponse, HealthResponse

logger = structlog.get_logger()

router = APIRouter(tags=["public"])

# Metrics
health_check_total = Counter(
    "odds_service_health_checks_total",
    "Total number of health check requests",
    ["route_type"]
)


@router.get("/", response_model=ServiceInfoResponse)
async def root() -> ServiceInfoResponse:
    """Get service information."""
    return ServiceInfoResponse(
        service=settings.service_name,
        version="0.1.0",
        status="running",
        environment=settings.environment,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    health_check_total.labels(route_type="public").inc()
    return HealthResponse(status="healthy")


@router.get("/liveness", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """
    Kubernetes liveness probe.

    Returns healthy if the process is running.
    """
    return HealthResponse(status="healthy")


@router.get("/readiness", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    """
    Kubernetes readiness probe.

    Returns healthy if service can accept traffic.
    For more sophisticated checks, verify DB/Redis connectivity here.
    """
    health_check_total.labels(route_type="public").inc()
    return HealthResponse(status="healthy")
