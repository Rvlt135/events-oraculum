from app.config.settings import settings as _settings, Settings


def get_settings() -> Settings:
    return _settings


# Re-export from sub-modules for convenience
from app.infrastructure.db.session import make_session_factory
from app.infrastructure.di.services import get_sports_service
from app.infrastructure.di.http import get_odds_api_client

__all__ = [
    "get_settings",
    "make_session_factory",
    "get_sports_service",
    "get_odds_api_client",
]
