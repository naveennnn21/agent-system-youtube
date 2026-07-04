"""Data models for YouTube analytics collection and reporting."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class YouTubeAnalyticsQuery:
    """Query parameters for YouTube Analytics API reports.query."""

    start_date: date
    end_date: date
    video_ids: list[str] = field(default_factory=list)
    ids: str = "channel==MINE"
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=lambda: ["video"])
    sort: str | None = None
    max_results: int | None = None

    def to_params(self) -> dict[str, str | int]:
        metrics = self.metrics or [
            "views",
            "estimatedMinutesWatched",
            "averageViewDuration",
            "averageViewPercentage",
            "subscribersGained",
            "likes",
            "comments",
            "shares",
        ]
        params: dict[str, str | int] = {
            "ids": self.ids,
            "startDate": self.start_date.isoformat(),
            "endDate": self.end_date.isoformat(),
            "metrics": ",".join(metrics),
            "dimensions": ",".join(self.dimensions),
        }
        if self.video_ids:
            params["filters"] = "video==" + ",".join(self.video_ids[:500])
        if self.sort:
            params["sort"] = self.sort
        elif "day" in self.dimensions:
            params["sort"] = "day"
        if self.max_results:
            params["maxResults"] = self.max_results
        return params


@dataclass(slots=True)
class AnalyticsSnapshot:
    """Normalized metrics for one YouTube video and snapshot date."""

    external_video_id: str
    snapshot_date: date
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: int = 0
    average_view_duration_seconds: float | None = None
    retention_rate: float | None = None
    click_through_rate: float | None = None
    subscribers_gained: int = 0
    revenue_estimate: float | None = None
    raw_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "external_video_id": self.external_video_id,
            "snapshot_date": self.snapshot_date.isoformat(),
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "watch_time_seconds": self.watch_time_seconds,
            "average_view_duration_seconds": self.average_view_duration_seconds,
            "retention_rate": self.retention_rate,
            "click_through_rate": self.click_through_rate,
            "subscribers_gained": self.subscribers_gained,
            "revenue_estimate": self.revenue_estimate,
            "raw_metrics": self.raw_metrics,
        }


@dataclass(slots=True)
class AnalyticsCollectionRequest:
    """Input for collecting and storing analytics snapshots."""

    start_date: date
    end_date: date
    external_video_ids: list[str] = field(default_factory=list)
    max_results: int = 100
    metrics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StoredAnalyticsSnapshot:
    """Stored snapshot result returned by the analytics agent."""

    analytics_id: uuid.UUID
    video_id: uuid.UUID
    upload_id: uuid.UUID | None
    external_video_id: str
    snapshot: AnalyticsSnapshot
    created: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "analytics_id": str(self.analytics_id),
            "video_id": str(self.video_id),
            "upload_id": str(self.upload_id) if self.upload_id else None,
            "external_video_id": self.external_video_id,
            "created": self.created,
            "snapshot": self.snapshot.to_dict(),
        }


@dataclass(slots=True)
class AnalyticsCollectionResult:
    """Result of one analytics collection run."""

    collected_count: int
    stored_count: int
    skipped_count: int
    snapshots: list[StoredAnalyticsSnapshot]
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collected_count": self.collected_count,
            "stored_count": self.stored_count,
            "skipped_count": self.skipped_count,
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "errors": self.errors,
        }


@dataclass(slots=True)
class AnalyticsReport:
    """Aggregated reporting layer output."""

    start_date: date
    end_date: date
    video_count: int
    total_views: int
    total_watch_time_seconds: int
    average_ctr: float | None
    average_retention: float | None
    subscribers_gained: int
    top_videos: list[dict[str, Any]]
    daily_totals: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "video_count": self.video_count,
            "total_views": self.total_views,
            "total_watch_time_seconds": self.total_watch_time_seconds,
            "average_ctr": self.average_ctr,
            "average_retention": self.average_retention,
            "subscribers_gained": self.subscribers_gained,
            "top_videos": self.top_videos,
            "daily_totals": self.daily_totals,
        }
