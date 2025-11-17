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

    service_name: str = Field(default="odds-service")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    redis_broker_url: str = Field(default="redis://localhost:6379/0")
    redis_cache_url: str = Field(default="redis://localhost:6379/1")

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="layerbit")

    odds_api_key: str = Field(default="")
    odds_api_base_url: str = Field(default="https://api.the-odds-api.com/v4")
    odds_api_regions: List[str] = Field(default=["eu"])
    odds_api_markets: List[str] = Field(default=["h2h"])
    odds_api_competitions: List[str] = Field(default=["soccer_uefa_champs_league"])
    
    # Odds mock configuration
    odds_use_mock: bool

    schedule_crons: List[str]
    schedule_sports_crons: List[str]
    catalog_cache_ttl: int = Field(default=604800)
    cache_ttl_sports_sec: int = Field(default=604800)
    cache_ttl_competitions_sec: int = Field(default=604800)
    cache_ttl_events_sec: int = Field(default=604800)
    cache_ttl_events_upcoming_sec: int = Field(default=604800)
    cache_ttl_odds_sec: int = Field(default=604800)


    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8083)

    admin_enabled: bool = Field(default=True)
    admin_prefix: str = Field(default="/_admin")
    admin_token: str = Field(default="")
    admin_docs_enabled: bool = Field(default=False)

    # AI Provider API Keys
    openrouter_api_key: str
    openrouter_base_url: str
    openai_api_key: str
    openai_base_url: str
    anthropic_api_key: str
    anthropic_base_url: str

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
