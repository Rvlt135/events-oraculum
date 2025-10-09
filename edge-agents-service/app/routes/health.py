from fastapi import APIRouter
import structlog

from app.config.settings import settings

router = APIRouter(prefix="/_agents", tags=["Health"])

logger = structlog.get_logger()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": "0.1.0"
    }
