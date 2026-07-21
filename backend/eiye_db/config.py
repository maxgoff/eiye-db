"""Configuration management with environment variable support (EIYE_ prefix)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EIYE_", env_file=".env")

    app_name: str = "eiye_db"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Metadata store (registry + audit)
    database_url: str = "sqlite:///./eiye.db"

    # Governance: unset api_key = open dev mode; admin key may view raw PII
    api_key: str | None = None
    admin_api_key: str | None = None


settings = Settings()
