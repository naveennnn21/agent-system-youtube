from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qs

import httpx
import pytest

from app.agents.youtube_upload import YouTubeUploadAgent
from app.models.enums import UploadPlatform, UploadStatus
from app.schemas.youtube_upload import YouTubeUploadResponse
from app.services.youtube import (
    GoogleOAuthClient,
    YouTubeDataAPIClient,
    YouTubeOAuthCredentials,
    YouTubeUploadError,
    YouTubeUploadRequest,
    YouTubeUploadResult,
)

pytestmark = pytest.mark.no_db


@dataclass
class FakeUploadRecord:
    video_id: uuid.UUID
    platform: UploadPlatform
    status: UploadStatus
    privacy_status: str
    request_payload: dict
    started_at: datetime
    external_video_id: str | None = None
    upload_url: str | None = None
    response_payload: dict | None = None
    uploaded_at: datetime | None = None
    error_message: str | None = None


class FakeUploadsRepository:
    def __init__(self) -> None:
        self.created: FakeUploadRecord | None = None
        self.updates: list[dict] = []

    async def create(self, **values):
        self.created = FakeUploadRecord(**values)
        return self.created

    async def update(self, instance: FakeUploadRecord, **values):
        self.updates.append(values)
        for key, value in values.items():
            setattr(instance, key, value)
        return instance


class FakeUploader:
    def __init__(self, result: YouTubeUploadResult | None = None, error: Exception | None = None) -> None:
        self.result = result or YouTubeUploadResult(
            video_id="yt123",
            video_url="https://www.youtube.com/watch?v=yt123",
            upload_status="processed",
            response_payload={"id": "yt123", "status": {"uploadStatus": "processed"}},
        )
        self.error = error
        self.request: YouTubeUploadRequest | None = None

    async def upload_video(self, request: YouTubeUploadRequest) -> YouTubeUploadResult:
        self.request = request
        if self.error is not None:
            raise self.error
        return self.result


def _credentials() -> YouTubeOAuthCredentials:
    return YouTubeOAuthCredentials(
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
    )


def test_authorization_url_uses_upload_scope_and_offline_access() -> None:
    url = GoogleOAuthClient(_credentials()).build_authorization_url(
        redirect_uri="http://localhost/oauth/callback",
        state="state-123",
    )

    assert "client_id=client-id" in url
    assert "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.upload" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=state-123" in url


@pytest.mark.asyncio
async def test_oauth_refresh_posts_expected_form_and_returns_token() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["content_type"] = request.headers["content-type"]
        captured["form"] = parse_qs(request.content.decode())
        return httpx.Response(
            200,
            json={
                "access_token": "access-token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "https://www.googleapis.com/auth/youtube.upload",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        token = await GoogleOAuthClient(_credentials(), client=client).refresh_access_token()

    assert captured["url"] == "https://oauth2.googleapis.com/token"
    assert captured["content_type"] == "application/x-www-form-urlencoded"
    assert captured["form"] == {
        "client_id": ["client-id"],
        "client_secret": ["client-secret"],
        "refresh_token": ["refresh-token"],
        "grant_type": ["refresh_token"],
    }
    assert token.access_token == "access-token"
    assert token.token_type == "Bearer"


@pytest.mark.asyncio
async def test_youtube_client_uploads_video_with_schedule_and_returns_contract(tmp_path) -> None:
    video_path = tmp_path / "short.mp4"
    video_path.write_bytes(b"fake-video-bytes")
    captured: dict[str, object] = {"calls": []}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["calls"].append(str(request.url))
        if str(request.url) == "https://oauth2.googleapis.com/token":
            return httpx.Response(200, json={"access_token": "access-token", "token_type": "Bearer"})
        if str(request.url).startswith("https://www.googleapis.com/upload/youtube/v3/videos"):
            captured["session_auth"] = request.headers["authorization"]
            captured["upload_length"] = request.headers["x-upload-content-length"]
            captured["upload_type"] = request.headers["x-upload-content-type"]
            captured["query"] = dict(request.url.params)
            captured["resource"] = json.loads(request.content)
            return httpx.Response(
                200,
                headers={"Location": "https://upload.youtube.test/session/1"},
            )
        if str(request.url) == "https://upload.youtube.test/session/1":
            captured["put_auth"] = request.headers["authorization"]
            captured["put_length"] = request.headers["content-length"]
            captured["put_content_type"] = request.headers["content-type"]
            captured["uploaded_bytes"] = request.content
            return httpx.Response(
                201,
                json={"id": "abc123", "status": {"uploadStatus": "uploaded"}},
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        oauth_client = GoogleOAuthClient(_credentials(), client=client)
        youtube_client = YouTubeDataAPIClient(
            oauth_client=oauth_client,
            client=client,
        )
        result = await youtube_client.upload_video(
            YouTubeUploadRequest(
                video_path=str(video_path),
                title="7 AI Editing Tricks",
                description="Useful workflow for creators.",
                tags=["AI", "#AI", "YouTube Shorts"],
                privacy_status="public",
                publish_at=datetime(2026, 7, 10, 14, 0, tzinfo=UTC),
                notify_subscribers=False,
            )
        )

    assert result.to_dict() == {
        "video_id": "abc123",
        "video_url": "https://www.youtube.com/watch?v=abc123",
        "upload_status": "uploaded",
    }
    assert captured["session_auth"] == "Bearer access-token"
    assert captured["put_auth"] == "Bearer access-token"
    assert captured["upload_length"] == str(len(b"fake-video-bytes"))
    assert captured["upload_type"] == "video/mp4"
    assert captured["put_length"] == str(len(b"fake-video-bytes"))
    assert captured["put_content_type"] == "video/mp4"
    assert captured["uploaded_bytes"] == b"fake-video-bytes"
    assert captured["query"] == {
        "uploadType": "resumable",
        "part": "snippet,status",
        "notifySubscribers": "false",
    }
    assert captured["resource"] == {
        "snippet": {
            "title": "7 AI Editing Tricks",
            "description": "Useful workflow for creators.",
            "categoryId": "22",
            "tags": ["AI", "YouTube Shorts"],
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
            "publishAt": "2026-07-10T14:00:00Z",
        },
    }


@pytest.mark.asyncio
async def test_youtube_client_rejects_missing_video_file() -> None:
    oauth_client = GoogleOAuthClient(_credentials())
    youtube_client = YouTubeDataAPIClient(oauth_client=oauth_client)

    with pytest.raises(YouTubeUploadError, match="does not exist"):
        await youtube_client.upload_video(
            YouTubeUploadRequest(
                video_path="missing.mp4",
                title="A valid title",
            )
        )


@pytest.mark.asyncio
async def test_agent_persists_successful_upload_url(tmp_path) -> None:
    video_path = tmp_path / "short.mp4"
    video_path.write_bytes(b"video")
    repository = FakeUploadsRepository()
    uploader = FakeUploader()
    agent = YouTubeUploadAgent(uploader=uploader, uploads_repository=repository)
    db_video_id = uuid.uuid4()

    result = await agent.upload_video(
        YouTubeUploadRequest(
            video_path=str(video_path),
            title="Creator Workflow",
            video_id=db_video_id,
        )
    )

    assert result == {
        "video_id": "yt123",
        "video_url": "https://www.youtube.com/watch?v=yt123",
        "upload_status": "processed",
    }
    assert repository.created is not None
    assert repository.created.video_id == db_video_id
    assert repository.created.platform == UploadPlatform.YOUTUBE_SHORTS
    assert repository.created.status == UploadStatus.SUCCEEDED
    assert repository.created.external_video_id == "yt123"
    assert repository.created.upload_url == "https://www.youtube.com/watch?v=yt123"
    assert repository.created.response_payload == {
        "id": "yt123",
        "status": {"uploadStatus": "processed"},
    }
    assert repository.created.uploaded_at is not None


@pytest.mark.asyncio
async def test_agent_marks_upload_record_failed_when_upload_raises(tmp_path) -> None:
    video_path = tmp_path / "short.mp4"
    video_path.write_bytes(b"video")
    repository = FakeUploadsRepository()
    agent = YouTubeUploadAgent(
        uploader=FakeUploader(error=RuntimeError("quota exceeded")),
        uploads_repository=repository,
    )

    with pytest.raises(RuntimeError, match="quota exceeded"):
        await agent.upload(
            YouTubeUploadRequest(
                video_path=str(video_path),
                title="Creator Workflow",
                video_id=uuid.uuid4(),
            )
        )

    assert repository.created is not None
    assert repository.created.status == UploadStatus.FAILED
    assert repository.created.error_message == "quota exceeded"


def test_public_response_schema_accepts_agent_contract() -> None:
    response = YouTubeUploadResponse.model_validate(
        {
            "video_id": "abc123",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "upload_status": "uploaded",
        }
    )

    assert response.video_id == "abc123"
