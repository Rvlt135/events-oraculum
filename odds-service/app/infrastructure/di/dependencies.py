from app.config.settings import settings as _settings, Settings


def get_settings() -> Settings:
    return _settings


# Re-export from sub-modules for convenience
from app.infrastructure.db.session import get_db_session, get_session_factory
from app.infrastructure.сache.redis_client import get_redis
from app.infrastructure.di.services import get_sports_service
from app.infrastructure.di.http import get_odds_api_client
from app.infrastructure.di.lifecycle import initialize as initialize_infrastructure, dispose as dispose_infrastructure

__all__ = [
    "get_settings",
    "get_db_session",
    "get_session_factory",
    "get_redis",
    "get_sports_service",
    "get_odds_api_client",
    "initialize_infrastructure",
    "dispose_infrastructure",
]
