from typing import List, Literal
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

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="layerbit")

    llm_provider: Literal["openrouter", "litellm", "langchain"] = Field(default="openrouter")
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_model: str = Field(default="openai/gpt-4o-mini")

    llm_temperature: float = Field(default=0.7)
    llm_max_tokens: int = Field(default=500)
    llm_timeout: int = Field(default=30)

    default_leagues: List[str] = Field(default=["soccer_uefa_champs_league"])
    min_confidence_threshold: float = Field(default=0.0)

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
