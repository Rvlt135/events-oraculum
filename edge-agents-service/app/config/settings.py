from typing import List, Literal
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = Field(default="edge-agents-service")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8082)

    redis_cache_url: str = Field(default="redis://localhost:6379/0")
    redis_broker_url: str = Field(default="redis://localhost:6379/1")

    postgres_host: str = Field(default="0.0.0.0")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="layerbit")
    collector_api_key: str = Field(default="")
    collector_api_url: str = Field(default="http://0.0.0.0:8083")


    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    llm_client: Literal["instructor", "langchain", "litellm"] = Field(default="instructor")

    cache_ttl_competitions_sec: int = Field(default=86400)
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_max_retries: int = Field(default=3)
    openrouter_referer: str = Field(default="https://layerbit-oraculum.ai")
    openrouter_app_title: str = Field(default="Layerbit Oraculum AI")

    models_config_path: str = Field(default="app/config/models.yaml")
    prompts_config_path: str = Field(default="app/config/prompts/")
    active_model_name: str = Field(default="gpt-4o-mini")

    llm_timeout: int = Field(default=30)

    default_leagues: List[str] = Field(default=["soccer_uefa_champs_league"])
    min_confidence_threshold: float = Field(default=0.0)

    @property
    def models_config_full_path(self) -> Path:
        return Path(self.models_config_path)

    @property
    def prompts_config_full_path(self) -> Path:
        return Path(self.prompts_config_path)


settings = Settings()
