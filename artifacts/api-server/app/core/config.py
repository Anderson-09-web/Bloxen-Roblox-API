from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    api_key: str = Field(default="", validation_alias="API_KEY")
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    presence_interval: int = Field(default=60, ge=15, validation_alias="PRESENCE_INTERVAL")
    cache_ttl: int = Field(default=30, ge=0, validation_alias="CACHE_TTL")
    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")
    environment: str = Field(default="production", validation_alias="ENVIRONMENT")
    roblox_timeout: float = Field(default=8.0, gt=0, validation_alias="ROBLOX_TIMEOUT")
    roblox_retries: int = Field(default=2, ge=0, le=4, validation_alias="ROBLOX_RETRIES")
    verification_ttl: int = Field(default=600, ge=60, validation_alias="VERIFICATION_TTL")
    verification_max_attempts: int = Field(default=5, ge=1, le=20, validation_alias="VERIFICATION_MAX_ATTEMPTS")
    rate_limit_max_requests: int = Field(default=120, ge=1, validation_alias="RATE_LIMIT_MAX_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_WINDOW_SECONDS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_origins(cls, value: Any) -> str:
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        return str(value)

    @property
    def database_url_async(self) -> str:
        """Return an async SQLAlchemy URL, with a local-only development fallback."""
        value = self.database_url.strip()
        if not value:
            return "sqlite+aiosqlite:///./bloxen.db"
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()