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

    redis_url: str = Field(default="redis://localhost:6379/0")

    postgres_url: str

    llm_client: Literal["instructor", "langchain", "litellm"] = Field(default="instructor")

    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_max_retries: int = Field(default=3)
    openrouter_referer: str = Field(default="https://layerbit-oraculum.ai")
    openrouter_app_title: str = Field(default="Layerbit Oraculum AI")

    models_config_path: str = Field(default="app/config/models.yaml")
    active_model_name: str = Field(default="gpt-4o-mini")

    llm_timeout: int = Field(default=30)

    default_leagues: List[str] = Field(default=["soccer_uefa_champs_league"])
    min_confidence_threshold: float = Field(default=0.0)

    @property
    def models_config_full_path(self) -> Path:
        return Path(self.models_config_path)


settings = Settings()
