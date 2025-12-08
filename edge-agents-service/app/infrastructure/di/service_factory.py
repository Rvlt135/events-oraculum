from app.infrastructure.cache import RecommendationCache
from app.infrastructure.di.container import Container
from app.services.features import FeatureService
from app.services.recommendation.service import RecommendationService


def create_recommendation_service(container: Container) -> RecommendationService:
    recommendation_cache = RecommendationCache(container.redis_cache_client)

    return RecommendationService(session_factory=container.session_factory, cache=recommendation_cache)

def create_feature_service(container: Container) -> FeatureService:
    return FeatureService(session_factory=container.session_factory)