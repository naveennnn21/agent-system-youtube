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

from pydantic import Field, field_validator
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
    DB_POOL_SIZE: int = Field(default=20, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=1)

    # -- Redis -----------------------------------------------------------------
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=1)

    # -- External API Keys -----------------------------------------------------
    OPENAI_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # -- Claude script generation ---------------------------------------------
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_VERSION: str = "2023-06-01"
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    CLAUDE_MAX_TOKENS: int = Field(default=1200, ge=256, le=4096)
    CLAUDE_HTTP_TIMEOUT: float = Field(default=30.0, gt=0)
    SCRIPT_TARGET_SECONDS: int = Field(default=45, ge=30, le=60)

    # -- YouTube SEO generation -----------------------------------------------
    SEO_TITLE_MAX_LENGTH: int = Field(default=100, ge=40, le=100)
    SEO_DESCRIPTION_MAX_LENGTH: int = Field(default=5000, ge=500, le=5000)
    SEO_MAX_HASHTAGS: int = Field(default=8, ge=1, le=15)
    SEO_MAX_KEYWORDS: int = Field(default=20, ge=5, le=50)
    SEO_MIN_OVERALL_SCORE: float = Field(default=60.0, ge=0, le=100)

    # -- YouTube upload --------------------------------------------------------
    YOUTUBE_OAUTH_CLIENT_ID: str = ""
    YOUTUBE_OAUTH_CLIENT_SECRET: str = ""
    YOUTUBE_OAUTH_REFRESH_TOKEN: str = ""
    YOUTUBE_OAUTH_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    YOUTUBE_UPLOAD_SCOPE: str = "https://www.googleapis.com/auth/youtube.upload"
    YOUTUBE_API_BASE_URL: str = "https://www.googleapis.com"
    YOUTUBE_UPLOAD_BASE_URL: str = "https://www.googleapis.com/upload/youtube/v3"
    YOUTUBE_WATCH_URL_TEMPLATE: str = "https://www.youtube.com/watch?v={video_id}"
    YOUTUBE_UPLOAD_TIMEOUT: float = Field(default=120.0, gt=0)
    YOUTUBE_DEFAULT_CATEGORY_ID: str = "22"
    YOUTUBE_DEFAULT_PRIVACY_STATUS: Literal["private", "public", "unlisted"] = "private"
    YOUTUBE_NOTIFY_SUBSCRIBERS: bool = False
    YOUTUBE_SELF_DECLARED_MADE_FOR_KIDS: bool = False
    YOUTUBE_CONTAINS_SYNTHETIC_MEDIA: bool = True

    # -- Learning agent --------------------------------------------------------
    LEARNING_LOOKBACK_DAYS: int = Field(default=90, ge=1, le=730)
    LEARNING_TOP_N: int = Field(default=5, ge=1, le=50)
    LEARNING_MAX_SAMPLES: int = Field(default=500, ge=10, le=5000)
    LEARNING_MIN_VIEWS: int = Field(default=100, ge=0)
    LEARNING_MODEL_VERSION: str = "learning-agent-v1"

    # -- Analytics agent -------------------------------------------------------
    YOUTUBE_ANALYTICS_BASE_URL: str = "https://youtubeanalytics.googleapis.com/v2"
    YOUTUBE_ANALYTICS_SCOPE: str = "https://www.googleapis.com/auth/yt-analytics.readonly"
    YOUTUBE_ANALYTICS_IDS: str = "channel==MINE"
    YOUTUBE_ANALYTICS_METRICS: list[str] = [
        "views",
        "estimatedMinutesWatched",
        "averageViewDuration",
        "averageViewPercentage",
        "subscribersGained",
        "likes",
        "comments",
        "shares",
        "annotationClickThroughRate",
    ]
    YOUTUBE_ANALYTICS_LOOKBACK_DAYS: int = Field(default=7, ge=1, le=365)
    YOUTUBE_ANALYTICS_COLLECTION_LIMIT: int = Field(default=100, ge=1, le=500)
    YOUTUBE_ANALYTICS_HTTP_TIMEOUT: float = Field(default=60.0, gt=0)

    # -- Workflow --------------------------------------------------------------
    WORKFLOW_RETRY_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    WORKFLOW_RETRY_BASE_DELAY: float = Field(default=0.5, ge=0)
    WORKFLOW_RETRY_MAX_DELAY: float = Field(default=5.0, ge=0)

    # -- Voice generation ------------------------------------------------------
    AUDIO_STORAGE_PATH: str = "storage/audio"
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io"
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    ELEVENLABS_OUTPUT_FORMAT: str = "mp3_44100_128"
    ELEVENLABS_STABILITY: float = Field(default=0.45, ge=0, le=1)
    ELEVENLABS_SIMILARITY_BOOST: float = Field(default=0.8, ge=0, le=1)
    OPENAI_BASE_URL: str = "https://api.openai.com"
    OPENAI_TTS_MODEL: str = "gpt-4o-mini-tts"
    OPENAI_TTS_INSTRUCTIONS: str = ""
    VOICE_REGISTRY_JSON: str = ""
    VOICE_HTTP_TIMEOUT: float = Field(default=30.0, gt=0)
    VOICE_RETRY_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    VOICE_RETRY_BASE_DELAY: float = Field(default=0.5, ge=0)
    VOICE_RETRY_MAX_DELAY: float = Field(default=4.0, ge=0)

    # -- Visual generation -----------------------------------------------------
    VISUAL_STORAGE_PATH: str = "storage/visuals"
    FLUX_API_KEY: str = ""
    FLUX_BASE_URL: str = "https://api.bfl.ai"
    FLUX_GENERATE_ENDPOINT: str = "/v1/flux-pro-1.1"
    FLUX_RESULT_ENDPOINT: str = "/v1/get_result"
    FLUX_AUTH_HEADER: str = "x-key"
    FLUX_MODEL: str = "flux-pro-1.1"
    FLUX_POLL_INTERVAL: float = Field(default=1.0, ge=0)
    FLUX_POLL_ATTEMPTS: int = Field(default=30, ge=1, le=120)
    STABILITY_API_KEY: str = ""
    STABILITY_BASE_URL: str = "https://api.stability.ai"
    STABILITY_GENERATE_ENDPOINT: str = "/v2beta/stable-image/generate/core"
    STABILITY_MODEL: str = "stable-image-core"
    VISUAL_HTTP_TIMEOUT: float = Field(default=60.0, gt=0)
    VISUAL_RETRY_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    VISUAL_RETRY_BASE_DELAY: float = Field(default=0.5, ge=0)
    VISUAL_RETRY_MAX_DELAY: float = Field(default=4.0, ge=0)
    VISUAL_WIDTH: int = Field(default=1024, ge=256, le=2048)
    VISUAL_HEIGHT: int = Field(default=1792, ge=256, le=2048)
    VISUAL_MAX_SCENES: int = Field(default=6, ge=1, le=12)
    VISUAL_STYLE: str = "cinematic, vertical YouTube Short, high detail"

    # -- Video editing ---------------------------------------------------------
    VIDEO_STORAGE_PATH: str = "storage/videos"
    FFMPEG_BINARY: str = "ffmpeg"
    FFPROBE_BINARY: str = "ffprobe"
    VIDEO_WIDTH: int = Field(default=1080, ge=720, le=2160)
    VIDEO_HEIGHT: int = Field(default=1920, ge=1280, le=3840)
    VIDEO_FPS: int = Field(default=30, ge=24, le=60)
    VIDEO_CRF: int = Field(default=18, ge=12, le=30)
    VIDEO_PRESET: str = "veryfast"
    VIDEO_AUDIO_BITRATE: str = "192k"
    VIDEO_MAX_DURATION_SECONDS: int = Field(default=60, ge=1, le=180)
    VIDEO_MIN_DURATION_SECONDS: int = Field(default=30, ge=1, le=180)
    VIDEO_SUBTITLE_FONT: str = "Arial"
    VIDEO_SUBTITLE_FONT_SIZE: int = Field(default=64, ge=24, le=120)
    VIDEO_SUBTITLE_PRIMARY_COLOR: str = "&H00FFFFFF"
    VIDEO_SUBTITLE_OUTLINE_COLOR: str = "&H00000000"
    VIDEO_SUBTITLE_BACK_COLOR: str = "&H80000000"

    # -- Trend research --------------------------------------------------------
    TREND_GEO: str = "US"
    TREND_MAX_RESULTS: int = Field(default=25, ge=1, le=100)
    TREND_HTTP_TIMEOUT: float = Field(default=10.0, gt=0)
    TREND_REDDIT_SUBREDDITS: list[str] = [
        "youtube",
        "technology",
        "ArtificialInteligence",
        "SideProject",
    ]
    REDDIT_USER_AGENT: str = "youtube-shorts-agent/0.1"

    # -- Logging ---------------------------------------------------------------
    LOG_LEVEL: str = "DEBUG"

    # -- CORS ------------------------------------------------------------------
    CORS_ORIGINS: list[str] = ["*"]

    # -- Celery ----------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_EAGER_PROPAGATES: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = Field(default=1, ge=1, le=128)
    CELERY_WORKER_CONCURRENCY: int = Field(default=2, ge=1, le=16)
    CELERY_TASK_MAX_RETRIES: int = Field(default=3, ge=0, le=20)
    CELERY_TASK_RETRY_BACKOFF: int = Field(default=60, ge=1, le=3600)
    CELERY_TASK_RETRY_BACKOFF_MAX: int = Field(default=600, ge=1, le=86400)
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(default=6900, ge=60)
    CELERY_TASK_TIME_LIMIT: int = Field(default=7200, ge=60)

    # -- Automation ------------------------------------------------------------
    AUTOMATION_DAILY_SHORTS_COUNT: int = Field(default=3, ge=1, le=24)
    AUTOMATION_DAILY_CRON_HOUR: int = Field(default=9, ge=0, le=23)
    AUTOMATION_DAILY_CRON_MINUTE: int = Field(default=0, ge=0, le=59)
    AUTOMATION_SHORT_SPACING_MINUTES: int = Field(default=20, ge=0, le=240)
    AUTOMATION_DEFAULT_CATEGORY: str = "technology"
    AUTOMATION_AUTOSTART_QUEUE: str = "automation"
    AUTOMATION_SHORTS_QUEUE: str = "shorts"
    AUTOMATION_ANALYTICS_QUEUE: str = "analytics"
    AUTOMATION_NOTIFICATIONS_QUEUE: str = "notifications"
    AUTOMATION_QUEUE_NAMES: list[str] = [
        "automation",
        "shorts",
        "analytics",
        "notifications",
    ]
    NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATION_WEBHOOK_URL: str = ""
    NOTIFICATION_WEBHOOK_TIMEOUT: float = Field(default=10.0, gt=0)

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
        """Require a non-empty PostgreSQL URL using the asyncpg driver."""
        value = v.strip()
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the 'asyncpg' driver "
                "(e.g. postgresql+asyncpg://...)"
            )
        return value

    @field_validator("DATABASE_SYNC_URL")
    @classmethod
    def validate_database_sync_url(cls, v: str) -> str:
        """Require a non-empty synchronous PostgreSQL URL."""
        value = v.strip()
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_SYNC_URL must be a PostgreSQL URL")
        return value

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
