from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest

from app.agents.analytics import AnalyticsAgent
from app.models import Analytics
from app.models.enums import UploadPlatform
from app.schemas.analytics import AnalyticsCollectionResponse, AnalyticsReportResponse
from app.services.analytics import (
    AnalyticsCollectionRequest,
    AnalyticsReporter,
    AnalyticsSnapshot,
    YouTubeAnalyticsClient,
    YouTubeAnalyticsQuery,
    parse_analytics_response,
)
from app.services.youtube import GoogleOAuthClient, YouTubeOAuthCredentials

pytestmark = pytest.mark.no_db


class FakeCollector:
    def __init__(self, snapshots: list[AnalyticsSnapshot]) -> None:
        self.snapshots = snapshots
        self.query: YouTubeAnalyticsQuery | None = None

    async def fetch_video_metrics(self, query: YouTubeAnalyticsQuery) -> list[AnalyticsSnapshot]:
        self.query = query
        return self.snapshots


class FakeUploadsRepository:
    def __init__(self, uploads: list[SimpleNamespace]) -> None:
        self.uploads = uploads

    async def list_successful_youtube_uploads(self, *, limit: int = 100, offset: int = 0):
        return self.uploads[offset : offset + limit]


class FakeAnalyticsRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[uuid.UUID, date], SimpleNamespace] = {}

    async def get_snapshot(self, video_id, snapshot_date, platform=UploadPlatform.YOUTUBE_SHORTS):
        return self.records.get((video_id, snapshot_date))

    async def create(self, **values):
        record = SimpleNamespace(id=uuid.uuid4(), **values)
        self.records[(record.video_id, record.snapshot_date)] = record
        return record

    async def update(self, instance, **values):
        for key, value in values.items():
            setattr(instance, key, value)
        return instance

    async def list_between(self, *, start_date, end_date, platform=UploadPlatform.YOUTUBE_SHORTS, offset=0, limit=1000):
        records = [
            record for (_, snapshot_date), record in self.records.items()
            if start_date <= snapshot_date <= end_date
        ]
        return records[offset : offset + limit]


def _credentials() -> YouTubeOAuthCredentials:
    return YouTubeOAuthCredentials(
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
    )


def test_parse_youtube_analytics_response_maps_required_metrics() -> None:
    query = YouTubeAnalyticsQuery(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        video_ids=["abc123"],
        dimensions=["video", "day"],
        metrics=[
            "views",
            "estimatedMinutesWatched",
            "averageViewDuration",
            "averageViewPercentage",
            "impressionsClickThroughRate",
            "subscribersGained",
            "likes",
            "comments",
            "shares",
        ],
    )
    payload = {
        "columnHeaders": [
            {"name": "video"},
            {"name": "day"},
            {"name": "views"},
            {"name": "estimatedMinutesWatched"},
            {"name": "averageViewDuration"},
            {"name": "averageViewPercentage"},
            {"name": "impressionsClickThroughRate"},
            {"name": "subscribersGained"},
            {"name": "likes"},
            {"name": "comments"},
            {"name": "shares"},
        ],
        "rows": [["abc123", "2026-07-02", 1000, 250.5, 32.7, 82.4, 12.5, 9, 88, 11, 24]],
    }

    snapshots = parse_analytics_response(payload, query=query)

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.external_video_id == "abc123"
    assert snapshot.snapshot_date == date(2026, 7, 2)
    assert snapshot.views == 1000
    assert snapshot.watch_time_seconds == 15030
    assert snapshot.average_view_duration_seconds == 32.7
    assert snapshot.retention_rate == 0.824
    assert snapshot.click_through_rate == 0.125
    assert snapshot.subscribers_gained == 9
    assert snapshot.likes == 88
    assert snapshot.comments == 11
    assert snapshot.shares == 24


@pytest.mark.asyncio
async def test_youtube_analytics_client_sends_authorized_report_query() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://oauth2.googleapis.com/token":
            return httpx.Response(200, json={"access_token": "token", "token_type": "Bearer"})
        captured["authorization"] = request.headers["authorization"]
        captured["query"] = parse_qs(request.url.query.decode())
        return httpx.Response(
            200,
            json={
                "columnHeaders": [{"name": "video"}, {"name": "views"}],
                "rows": [["abc123", 100]],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        oauth_client = GoogleOAuthClient(_credentials(), client=client)
        analytics_client = YouTubeAnalyticsClient(
            oauth_client=oauth_client,
            client=client,
        )
        snapshots = await analytics_client.fetch_video_metrics(
            YouTubeAnalyticsQuery(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 2),
                video_ids=["abc123"],
                metrics=["views"],
                dimensions=["video"],
            )
        )

    assert captured["authorization"] == "Bearer token"
    assert captured["query"]["ids"] == ["channel==MINE"]
    assert captured["query"]["metrics"] == ["views"]
    assert captured["query"]["dimensions"] == ["video"]
    assert captured["query"]["filters"] == ["video==abc123"]
    assert snapshots[0].views == 100


@pytest.mark.asyncio
async def test_analytics_agent_upserts_snapshots_for_successful_uploads() -> None:
    video_id = uuid.uuid4()
    upload_id = uuid.uuid4()
    upload = SimpleNamespace(
        id=upload_id,
        video_id=video_id,
        external_video_id="abc123",
    )
    snapshot = AnalyticsSnapshot(
        external_video_id="abc123",
        snapshot_date=date(2026, 7, 2),
        views=1000,
        likes=80,
        comments=10,
        shares=20,
        watch_time_seconds=15000,
        retention_rate=0.82,
        click_through_rate=0.12,
        subscribers_gained=8,
        raw_metrics={"views": 1000},
    )
    collector = FakeCollector([snapshot])
    analytics_repository = FakeAnalyticsRepository()
    agent = AnalyticsAgent(
        collector=collector,
        analytics_repository=analytics_repository,
        uploads_repository=FakeUploadsRepository([upload]),
        metrics=["views"],
    )

    result = await agent.collect(
        AnalyticsCollectionRequest(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
            external_video_ids=["abc123"],
            max_results=10,
        )
    )

    assert result.collected_count == 1
    assert result.stored_count == 1
    assert result.snapshots[0].video_id == video_id
    assert result.snapshots[0].upload_id == upload_id
    assert collector.query is not None
    assert collector.query.video_ids == ["abc123"]
    stored = next(iter(analytics_repository.records.values()))
    assert stored.views == 1000
    assert stored.retention_rate == Decimal("0.82")
    assert stored.click_through_rate == Decimal("0.12")


def test_reporting_layer_aggregates_stored_metrics() -> None:
    records = [
        Analytics(
            id=uuid.uuid4(),
            video_id=uuid.uuid4(),
            snapshot_date=date(2026, 7, 1),
            views=100,
            likes=10,
            comments=2,
            shares=4,
            watch_time_seconds=2000,
            retention_rate=Decimal("0.75"),
            click_through_rate=Decimal("0.10"),
            subscribers_gained=3,
            raw_metrics={},
        ),
        Analytics(
            id=uuid.uuid4(),
            video_id=uuid.uuid4(),
            snapshot_date=date(2026, 7, 1),
            views=300,
            likes=30,
            comments=4,
            shares=9,
            watch_time_seconds=6000,
            retention_rate=Decimal("0.85"),
            click_through_rate=Decimal("0.20"),
            subscribers_gained=7,
            raw_metrics={},
        ),
    ]

    report = AnalyticsReporter().build_report(
        records,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        top_n=1,
    )

    assert report.total_views == 400
    assert report.total_watch_time_seconds == 8000
    assert report.average_retention == 0.825
    assert report.average_ctr == 0.175
    assert report.subscribers_gained == 10
    assert report.top_videos[0]["views"] == 300
    assert report.daily_totals == [
        {
            "date": "2026-07-01",
            "views": 400,
            "watch_time_seconds": 8000,
            "subscribers_gained": 10,
        }
    ]


def test_public_analytics_schemas_accept_contracts() -> None:
    collection = AnalyticsCollectionResponse.model_validate(
        {
            "collected_count": 1,
            "stored_count": 1,
            "skipped_count": 0,
            "snapshots": [
                {
                    "analytics_id": str(uuid.uuid4()),
                    "video_id": str(uuid.uuid4()),
                    "upload_id": None,
                    "external_video_id": "abc123",
                    "created": True,
                    "snapshot": {"views": 100},
                }
            ],
            "errors": [],
        }
    )
    report = AnalyticsReportResponse.model_validate(
        {
            "start_date": "2026-07-01",
            "end_date": "2026-07-02",
            "video_count": 1,
            "total_views": 100,
            "total_watch_time_seconds": 500,
            "average_ctr": 0.1,
            "average_retention": 0.8,
            "subscribers_gained": 3,
            "top_videos": [],
            "daily_totals": [],
        }
    )

    assert collection.collected_count == 1
    assert report.total_views == 100
