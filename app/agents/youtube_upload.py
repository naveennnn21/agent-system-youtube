"""YouTube Upload Agent using YouTube Data API v3."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.models.enums import UploadPlatform, UploadStatus
from app.repositories import UploadsRepository
from app.services.youtube import (
    GoogleOAuthClient,
    YouTubeDataAPIClient,
    YouTubeOAuthCredentials,
    YouTubeUploadRequest,
    YouTubeUploadResult,
)


class YouTubeUploader(Protocol):
    async def upload_video(self, request: YouTubeUploadRequest) -> YouTubeUploadResult:
        """Upload a video and return a YouTube upload result."""


class YouTubeUploadAgent:
    """Upload rendered Shorts to YouTube and persist the resulting watch URL."""

    def __init__(
        self,
        *,
        uploader: YouTubeUploader,
        uploads_repository: UploadsRepository | None = None,
    ) -> None:
        self.uploader = uploader
        self.uploads_repository = uploads_repository

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        uploads_repository: UploadsRepository | None = None,
    ) -> "YouTubeUploadAgent":
        """Create the production OAuth-backed upload agent."""
        settings = settings or get_settings()
        credentials = YouTubeOAuthCredentials(
            client_id=settings.YOUTUBE_OAUTH_CLIENT_ID,
            client_secret=settings.YOUTUBE_OAUTH_CLIENT_SECRET,
            refresh_token=settings.YOUTUBE_OAUTH_REFRESH_TOKEN,
            token_uri=settings.YOUTUBE_OAUTH_TOKEN_URI,
            scope=settings.YOUTUBE_UPLOAD_SCOPE,
        )
        oauth_client = GoogleOAuthClient(
            credentials,
            timeout=settings.YOUTUBE_UPLOAD_TIMEOUT,
        )
        uploader = YouTubeDataAPIClient(
            oauth_client=oauth_client,
            api_base_url=settings.YOUTUBE_API_BASE_URL,
            upload_base_url=settings.YOUTUBE_UPLOAD_BASE_URL,
            watch_url_template=settings.YOUTUBE_WATCH_URL_TEMPLATE,
            timeout=settings.YOUTUBE_UPLOAD_TIMEOUT,
        )
        return cls(uploader=uploader, uploads_repository=uploads_repository)

    async def upload_video(
        self,
        request: YouTubeUploadRequest,
    ) -> dict[str, str]:
        """Return exactly ``video_id/video_url/upload_status``."""
        result = await self.upload(request)
        return result.to_dict()

    async def upload(self, request: YouTubeUploadRequest) -> YouTubeUploadResult:
        """Upload a video and store its URL when a repository is configured."""
        upload_record = None
        if self.uploads_repository is not None and request.video_id is not None:
            upload_record = await self.uploads_repository.create(
                video_id=request.video_id,
                platform=UploadPlatform.YOUTUBE_SHORTS,
                status=UploadStatus.UPLOADING,
                privacy_status=request.effective_privacy_status,
                request_payload=_request_payload(request),
                started_at=datetime.now(UTC),
            )

        try:
            result = await self.uploader.upload_video(request)
        except Exception as exc:
            if upload_record is not None and self.uploads_repository is not None:
                await self.uploads_repository.update(
                    upload_record,
                    status=UploadStatus.FAILED,
                    error_message=str(exc),
                    response_payload={},
                )
            raise

        if upload_record is not None and self.uploads_repository is not None:
            await self.uploads_repository.update(
                upload_record,
                external_video_id=result.video_id,
                upload_url=result.video_url,
                status=UploadStatus.SUCCEEDED,
                response_payload=result.response_payload,
                uploaded_at=datetime.now(UTC),
            )

        return result


def _request_payload(request: YouTubeUploadRequest) -> dict[str, Any]:
    payload = request.to_video_resource()
    payload["video_path"] = request.video_path
    payload["mime_type"] = request.upload_mime_type
    payload["notify_subscribers"] = request.notify_subscribers
    payload["metadata"] = request.metadata
    return payload
