"""
app.core.config
~~~~~~~~~~~~~~~~
Centralised application settings powered by pydantic-settings.

All values are read from environment variables (or an ``.env`` file).
Use ``get_settings()`` in application code — it returns a cached singleton
so the ``.env`` file is parsed only once per process.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration sourced from env vars / .env file."""

    # -- Application -----------------------------------------------------------
    APP_NAME: str = "youtube_shorts_agent"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # -- API Server ------------------------------------------------------------
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # -- Database (async — used by SQLAlchemy async engine) --------------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/youtube_shorts_agent"

    # -- Database (sync — used by Alembic migrations) --------------------------
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@db:5432/youtube_shorts_agent"

    # -- Redis -----------------------------------------------------------------
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_MAX_CONNECTIONS: int = 20

    # -- External API Keys -----------------------------------------------------
    OPENAI_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""

    # -- Logging ---------------------------------------------------------------
    LOG_LEVEL: str = "DEBUG"

    # -- CORS ------------------------------------------------------------------
    CORS_ORIGINS: list[str] = ["*"]

    # -- Celery ----------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # -- Pydantic-settings configuration ---------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -- Validators ------------------------------------------------------------

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure LOG_LEVEL is an accepted Python logging level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(
                f"LOG_LEVEL must be one of {allowed}, got '{v}'"
            )
        return upper

    @field_validator("API_PORT")
    @classmethod
    def validate_api_port(cls, v: int) -> int:
        """Ensure the port number is within the valid range."""
        if not (1 <= v <= 65535):
            raise ValueError(
                f"API_PORT must be between 1 and 65535, got {v}"
            )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Basic check: the async DB URL must use the asyncpg driver."""
        if "asyncpg" not in v:
            raise ValueError(
                "DATABASE_URL must use the 'asyncpg' driver "
                "(e.g. postgresql+asyncpg://...)"
            )
        return v

    # -- Convenience properties ------------------------------------------------

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` singleton.

    Using ``@lru_cache`` ensures the ``.env`` file is read only once.
    """
    return Settings()
