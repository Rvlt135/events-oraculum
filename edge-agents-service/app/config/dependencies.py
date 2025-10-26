from app.config.settings import settings as _settings, Settings


def get_settings() -> Settings:
    return _settings
