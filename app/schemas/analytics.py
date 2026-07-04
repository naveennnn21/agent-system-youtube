"""Pydantic schemas for analytics collection and reporting APIs."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AnalyticsCollectionRequestSchema(BaseModel):
    """Request body for collecting YouTube analytics metrics."""

    start_date: date
    end_date: date
    external_video_ids: list[str] = Field(default_factory=list)
    max_results: int = Field(default=100, ge=1, le=500)
    metrics: list[str] = Field(default_factory=list)

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, value: date, info):
        start_date = info.data.get("start_date")
        if start_date and value < start_date:
            raise ValueError("end_date must be on or after start_date.")
        return value


class AnalyticsSnapshotResponse(BaseModel):
    """Stored analytics snapshot API response."""

    analytics_id: str
    video_id: str
    upload_id: str | None = None
    external_video_id: str
    created: bool
    snapshot: dict[str, Any]


class AnalyticsCollectionResponse(BaseModel):
    """Analytics collection API response."""

    collected_count: int = Field(ge=0)
    stored_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    snapshots: list[AnalyticsSnapshotResponse]
    errors: list[str] = Field(default_factory=list)


class AnalyticsMetricResponse(BaseModel):
    """Stored metric row response."""

    analytics_id: str
    video_id: str
    upload_id: str | None = None
    snapshot_date: date
    views: int
    likes: int
    comments: int
    shares: int
    watch_time_seconds: int
    average_view_duration_seconds: float | None = None
    retention_rate: float | None = None
    click_through_rate: float | None = None
    subscribers_gained: int
    revenue_estimate: float | None = None
    raw_metrics: dict[str, Any]


class AnalyticsReportResponse(BaseModel):
    """Aggregate analytics report response."""

    start_date: date
    end_date: date
    video_count: int
    total_views: int
    total_watch_time_seconds: int
    average_ctr: float | None = None
    average_retention: float | None = None
    subscribers_gained: int
    top_videos: list[dict[str, Any]]
    daily_totals: list[dict[str, Any]]
