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

    service_name: str = Field(default="gateway-service")
    environment: str = Field(default="production")
    log_level: str = Field(default="INFO")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8080)

    api_key: str = Field(default="changeme_secret_key")

    redis_url: str = Field(default="redis://localhost:6379/0")

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="layerbit")

    default_page_limit: int = Field(default=50)
    max_page_limit: int = Field(default=500)

    cors_origins: List[str] = Field(default=["*"])

    cache_ttl_seconds: int = Field(default=300)

    jwt_secret: str = Field(default="changeme_jwt_secret_min_32_chars")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_seconds: int = Field(default=900)
    refresh_token_ttl_seconds: int = Field(default=1209600)

    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_redirect_uri: str = Field(default="http://localhost:8080/auth/google/callback")

    password_hash_scheme: str = Field(default="argon2")

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
