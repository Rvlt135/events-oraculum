import structlog
from fastapi import APIRouter

# from app.api.deps import get_recommendation_service
# from app.services.legacy.service import RecommendationService

router = APIRouter(prefix="/_agents", tags=["Recommendations"])

logger = structlog.get_logger()

