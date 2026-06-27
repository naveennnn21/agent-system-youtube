"""Shared enum values used by ORM models."""

from __future__ import annotations

from enum import Enum


class TopicStatus(str, Enum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ScriptStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class VideoStatus(str, Enum):
    PLANNED = "planned"
    RENDERING = "rendering"
    RENDERED = "rendered"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class UploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"


class UploadPlatform(str, Enum):
    YOUTUBE_SHORTS = "youtube_shorts"


class FeedbackType(str, Enum):
    PERFORMANCE = "performance"
    QUALITY = "quality"
    AUDIENCE = "audience"
    SYSTEM = "system"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return database values for SQLAlchemy Enum columns."""
    return [str(member.value) for member in enum_cls]
