"""Data models for YouTube Data API uploads."""

from __future__ import annotations

import mimetypes
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

PrivacyStatus = Literal["private", "public", "unlisted"]


@dataclass(slots=True)
class YouTubeOAuthCredentials:
    """OAuth client credentials used to refresh a YouTube upload token."""

    client_id: str
    client_secret: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"
    scope: str = "https://www.googleapis.com/auth/youtube.upload"

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("client_id", self.client_id),
                ("client_secret", self.client_secret),
                ("refresh_token", self.refresh_token),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                "Missing YouTube OAuth credential values: " + ", ".join(missing)
            )


@dataclass(slots=True)
class OAuthToken:
    """Bearer token returned by Google's OAuth token endpoint."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    scope: str | None = None


@dataclass(slots=True)
class YouTubeUploadRequest:
    """Input required to upload and optionally schedule a YouTube video."""

    video_path: str
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category_id: str = "22"
    privacy_status: PrivacyStatus = "private"
    publish_at: datetime | None = None
    default_language: str | None = "en"
    self_declared_made_for_kids: bool = False
    contains_synthetic_media: bool = True
    notify_subscribers: bool = False
    mime_type: str | None = None
    video_id: uuid.UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.title = " ".join(self.title.split())
        self.description = self.description.strip()
        self.tags = _dedupe_tags(self.tags)
        if not self.title:
            raise ValueError("YouTube upload title cannot be empty.")
        if len(self.title) > 100:
            raise ValueError("YouTube upload title cannot exceed 100 characters.")
        if self.privacy_status not in {"private", "public", "unlisted"}:
            raise ValueError("privacy_status must be private, public, or unlisted.")

    @property
    def path(self) -> Path:
        return Path(self.video_path)

    @property
    def file_size(self) -> int:
        return self.path.stat().st_size

    @property
    def upload_mime_type(self) -> str:
        if self.mime_type:
            return self.mime_type
        guessed, _ = mimetypes.guess_type(self.video_path)
        if guessed and guessed.startswith("video/"):
            return guessed
        return "video/mp4"

    @property
    def effective_privacy_status(self) -> PrivacyStatus:
        if self.publish_at is not None:
            return "private"
        return self.privacy_status

    @property
    def normalized_publish_at(self) -> str | None:
        if self.publish_at is None:
            return None
        value = self.publish_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    def to_video_resource(self) -> dict[str, Any]:
        snippet: dict[str, Any] = {
            "title": self.title,
            "description": self.description,
            "categoryId": str(self.category_id),
        }
        if self.tags:
            snippet["tags"] = self.tags
        if self.default_language:
            snippet["defaultLanguage"] = self.default_language

        status: dict[str, Any] = {
            "privacyStatus": self.effective_privacy_status,
            "selfDeclaredMadeForKids": self.self_declared_made_for_kids,
            "containsSyntheticMedia": self.contains_synthetic_media,
        }
        if self.normalized_publish_at:
            status["publishAt"] = self.normalized_publish_at

        return {"snippet": snippet, "status": status}


@dataclass(slots=True)
class YouTubeUploadResult:
    """Public upload result with raw API payload for persistence."""

    video_id: str
    video_url: str
    upload_status: str
    response_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        return {
            "video_id": self.video_id,
            "video_url": self.video_url,
            "upload_status": self.upload_status,
        }


def _dedupe_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = " ".join(str(tag).strip().lstrip("#").split())
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            normalized.append(cleaned[:500])
    return normalized
