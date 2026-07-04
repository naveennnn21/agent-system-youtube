"""Pydantic schemas for dashboard APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DashboardMetric(BaseModel):
    """One overview metric card."""

    label: str
    value: int | float | str | None
    detail: str | None = None


class DashboardTrendPoint(BaseModel):
    """Daily analytics point for charts."""

    date: date
    views: int
    watch_time_seconds: int
    average_ctr: float | None = None
    average_retention: float | None = None


class DashboardOverviewResponse(BaseModel):
    """High-level dashboard overview response."""

    metrics: list[DashboardMetric]
    video_status_counts: dict[str, int]
    upload_status_counts: dict[str, int]
    trend: list[DashboardTrendPoint]


class DashboardVideoResponse(BaseModel):
    """Video row shown in the dashboard."""

    id: str
    title: str
    status: str
    duration_seconds: int | None = None
    file_path: str | None = None
    thumbnail_path: str | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime
    latest_views: int = 0
    latest_retention_rate: float | None = None
    latest_ctr: float | None = None


class DashboardUploadResponse(BaseModel):
    """Upload status row shown in the dashboard."""

    id: str
    video_id: str
    video_title: str | None = None
    platform: str
    external_video_id: str | None = None
    upload_url: str | None = None
    status: str
    privacy_status: str
    error_message: str | None = None
    started_at: datetime | None = None
    uploaded_at: datetime | None = None
    created_at: datetime


class DashboardLearningInsightResponse(BaseModel):
    """Learning feedback row shown in the dashboard."""

    id: str
    feedback_type: str
    signal: str
    score: float | None = None
    notes: str | None = None
    recommendations: dict[str, Any] = Field(default_factory=dict)
    applied: bool
    model_version: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    video_id: str | None = None
    video_title: str | None = None


class DashboardAgentLogResponse(BaseModel):
    """Task and queue event rendered as an agent log row."""

    id: str
    level: str
    source: str
    message: str
    queue: str | None = None
    task_id: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardQueueResponse(BaseModel):
    """Queue management snapshot for dashboard logs."""

    queue_lengths: dict[str, int]
    logs: list[DashboardAgentLogResponse]
