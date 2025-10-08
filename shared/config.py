from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class DatabaseConfig(BaseConfig):
    supabase_url: str = Field(alias="VITE_SUPABASE_URL")
    supabase_anon_key: str = Field(alias="VITE_SUPABASE_SUPABASE_ANON_KEY")
    postgres_connection_string: str = ""

    @property
    def postgres_url(self) -> str:
        if self.postgres_connection_string:
            return self.postgres_connection_string
        base_url = self.supabase_url.replace("https://", "")
        project_ref = base_url.split(".")[0]
        return f"postgresql://postgres:[email protected]:6543/postgres"


class RedisConfig(BaseConfig):
    redis_url: str = Field(default="redis://localhost:6379/0")


class OddsAPIConfig(BaseConfig):
    odds_api_key: str = Field(default="", alias="ODDS_API_KEY")
    odds_api_base_url: str = Field(default="https://api.the-odds-api.com/v4")
    odds_api_regions: list[str] = Field(default=["eu"])
    odds_api_markets: list[str] = Field(default=["h2h"])
    odds_api_leagues: list[str] = Field(default=["soccer_uefa_champs_league"])


class AppConfig(BaseConfig):
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    odds_api: OddsAPIConfig = Field(default_factory=OddsAPIConfig)


def get_config() -> AppConfig:
    return AppConfig()
