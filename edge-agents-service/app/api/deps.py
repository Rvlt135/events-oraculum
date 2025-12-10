from fastapi import Depends, Request

from app.infrastructure.di.service_factory import create_recommendation_service
from app.services.legacy.service import RecommendationService


def get_recommendation_service(request: Request) -> RecommendationService:
    container = request.app.state.container
    return create_recommendation_service(container)