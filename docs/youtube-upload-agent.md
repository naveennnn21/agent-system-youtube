# YouTube Upload Agent

`YouTubeUploadAgent` uploads rendered Shorts through the YouTube Data API v3,
supports scheduled publishing, and stores the resulting watch URL in the
existing `uploads` table when an `UploadsRepository` is provided.

The implementation uses Google's OAuth refresh-token flow and the YouTube
resumable upload protocol:

1. Refresh `YOUTUBE_OAUTH_REFRESH_TOKEN` at `YOUTUBE_OAUTH_TOKEN_URI`.
2. Start a resumable upload session with `videos.insert`.
3. Upload the local MP4 bytes to the returned session URL.
4. Return and optionally persist the YouTube `video_id` and watch URL.

## Usage

```python
from datetime import UTC, datetime

from app.agents.youtube_upload import YouTubeUploadAgent
from app.services.youtube import YouTubeUploadRequest

agent = YouTubeUploadAgent.from_settings()
result = await agent.upload_video(
    YouTubeUploadRequest(
        video_path="storage/videos/short.mp4",
        title="7 AI Editing Tricks That Save Hours",
        description="A fast workflow for creating better YouTube Shorts.",
        tags=["AI video editing", "YouTube Shorts", "creator tools"],
        publish_at=datetime(2026, 7, 10, 14, 0, tzinfo=UTC),
    )
)
```

Public output:

```json
{
  "video_id": "abc123",
  "video_url": "https://www.youtube.com/watch?v=abc123",
  "upload_status": "uploaded"
}
```

When `publish_at` is set, the request uses `privacyStatus=private`, which is
required by YouTube for scheduled publishing.

## Configuration

- `YOUTUBE_OAUTH_CLIENT_ID`
- `YOUTUBE_OAUTH_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REFRESH_TOKEN`
- `YOUTUBE_OAUTH_TOKEN_URI`
- `YOUTUBE_UPLOAD_SCOPE`
- `YOUTUBE_UPLOAD_BASE_URL`
- `YOUTUBE_WATCH_URL_TEMPLATE`
- `YOUTUBE_UPLOAD_TIMEOUT`
- `YOUTUBE_DEFAULT_CATEGORY_ID`
- `YOUTUBE_DEFAULT_PRIVACY_STATUS`
