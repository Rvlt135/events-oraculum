from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Основные настройки - обязательные из env
    service_name: str
    environment: str
    log_level: str

    # API настройки - обязательные из env
    api_host: str
    api_port: int
    api_key: str  # Секретный ключ - обязательно из env

    # Redis - обязательные из env
    redis_url: str

    # PostgreSQL - обязательные из env
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    # Пагинация - можно оставить дефолты или брать из env
    default_page_limit: int = Field(default=50)
    max_page_limit: int = Field(default=500)

    # CORS - можно оставить дефолт или брать из env
    cors_origins: List[str] = Field(default=["*"])

    # Кеш - можно оставить дефолт или брать из env
    cache_ttl_seconds: int = Field(default=300)

    # JWT - обязательные из env (без дефолтов для безопасности)
    jwt_secret: str  # Секретный ключ - обязательно из env
    jwt_algorithm: str = Field(default="HS256")  # Алгоритм редко меняется
    access_token_ttl_seconds: int = Field(default=86400)  # 1 день (24 часа)
    refresh_token_ttl_seconds: int = Field(default=1209600)  # 14 дней

    # Cookies settings
    access_token_cookie_name: str = Field(default="access_token")
    refresh_token_cookie_name: str = Field(default="refresh_token")
    auth_cookie_domain: str = Field(default="")
    auth_cookie_secure: bool = Field(default=True)
    auth_access_ttl_sec: int = Field(default=3600)
    auth_refresh_ttl_sec: int = Field(default=2592000)


    # Google OAuth - опциональные, можно оставить пустые строки
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_redirect_uri: str = Field(default="http://localhost:8080/auth/google/callback")

    # Telegram - опциональные
    telegram_bot_token: str = Field(default="")
    telegram_max_auth_age_seconds: int = Field(default=600)

    # Password hashing - алгоритм редко меняется
    password_hash_scheme: str = Field(default="argon2")

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
