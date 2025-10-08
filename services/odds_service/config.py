from pydantic import Field
from shared.config import BaseConfig, DatabaseConfig, OddsAPIConfig, RedisConfig


class OddsServiceConfig(BaseConfig):
    service_name: str = Field(default="odds-service")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    odds_api: OddsAPIConfig = Field(default_factory=OddsAPIConfig)

    collection_interval_hours: int = Field(default=12)


def get_odds_service_config() -> OddsServiceConfig:
    return OddsServiceConfig()
