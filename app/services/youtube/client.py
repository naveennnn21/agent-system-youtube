"""Async YouTube Data API v3 upload client."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.services.youtube.models import YouTubeUploadRequest, YouTubeUploadResult
from app.services.youtube.oauth import GoogleOAuthClient


class YouTubeUploadError(RuntimeError):
    """Raised when YouTube upload setup or transfer fails."""


class YouTubeDataAPIClient:
    """Upload videos using YouTube Data API v3 resumable uploads."""

    def __init__(
        self,
        *,
        oauth_client: GoogleOAuthClient,
        api_base_url: str = "https://www.googleapis.com",
        upload_base_url: str = "https://www.googleapis.com/upload/youtube/v3",
        watch_url_template: str = "https://www.youtube.com/watch?v={video_id}",
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.oauth_client = oauth_client
        self.api_base_url = api_base_url.rstrip("/")
        self.upload_base_url = upload_base_url.rstrip("/")
        self.watch_url_template = watch_url_template
        self.timeout = timeout
        self._client = client

    async def upload_video(self, request: YouTubeUploadRequest) -> YouTubeUploadResult:
        """Upload a local video and return the public result contract."""
        if not request.path.exists() or not request.path.is_file():
            raise YouTubeUploadError(f"Video file does not exist: {request.video_path}")
        if request.file_size <= 0:
            raise YouTubeUploadError(f"Video file is empty: {request.video_path}")

        token = await self.oauth_client.refresh_access_token()
        headers = {"Authorization": f"{token.token_type} {token.access_token}"}

        if self._client is not None:
            session_url = await self._start_resumable_session(request, headers, self._client)
            payload = await self._upload_file(request, headers, session_url, self._client)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                session_url = await self._start_resumable_session(request, headers, client)
                payload = await self._upload_file(request, headers, session_url, client)

        video_id = payload.get("id")
        if not isinstance(video_id, str) or not video_id:
            raise YouTubeUploadError("YouTube upload response did not include a video id.")

        upload_status = (
            payload.get("status", {}).get("uploadStatus")
            if isinstance(payload.get("status"), dict)
            else None
        ) or "uploaded"
        return YouTubeUploadResult(
            video_id=video_id,
            video_url=self.watch_url_template.format(video_id=video_id),
            upload_status=str(upload_status),
            response_payload=payload,
        )

    async def _start_resumable_session(
        self,
        request: YouTubeUploadRequest,
        auth_headers: dict[str, str],
        client: httpx.AsyncClient,
    ) -> str:
        params: dict[str, Any] = {
            "uploadType": "resumable",
            "part": "snippet,status",
            "notifySubscribers": str(request.notify_subscribers).lower(),
        }
        body = request.to_video_resource()
        response = await client.post(
            f"{self.upload_base_url}/videos",
            params=params,
            json=body,
            headers={
                **auth_headers,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(request.file_size),
                "X-Upload-Content-Type": request.upload_mime_type,
            },
        )
        if response.status_code >= 400:
            raise YouTubeUploadError(
                "Failed to start YouTube resumable upload session "
                f"(HTTP {response.status_code}): {response.text}"
            )
        session_url = response.headers.get("Location")
        if not session_url:
            raise YouTubeUploadError("YouTube upload session response missing Location header.")
        return session_url

    async def _upload_file(
        self,
        request: YouTubeUploadRequest,
        auth_headers: dict[str, str],
        session_url: str,
        client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        response = await client.put(
            session_url,
            content=_iter_file_chunks(request.path),
            headers={
                **auth_headers,
                "Content-Length": str(request.file_size),
                "Content-Type": request.upload_mime_type,
            },
        )
        if response.status_code == 308:
            raise YouTubeUploadError(
                "YouTube reported an incomplete resumable upload; retry is required."
            )
        if response.status_code not in {200, 201}:
            raise YouTubeUploadError(
                f"YouTube video upload failed (HTTP {response.status_code}): {response.text}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise YouTubeUploadError("YouTube upload response must be a JSON object.")
        return payload


async def _iter_file_chunks(path, chunk_size: int = 8 * 1024 * 1024) -> AsyncIterator[bytes]:
    with path.open("rb") as video_file:
        while True:
            chunk = await asyncio.to_thread(video_file.read, chunk_size)
            if not chunk:
                break
            yield chunk
