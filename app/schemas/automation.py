"""Pydantic schemas for automation and queue APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EnqueueShortRequest(BaseModel):
    """Request to enqueue one Short generation workflow."""

    metadata: dict[str, Any] = Field(default_factory=dict)


class DailyShortsRequest(BaseModel):
    """Request to schedule a batch of daily Shorts."""

    count: int | None = Field(default=None, ge=1, le=24)
    category: str | None = None
    base_metadata: dict[str, Any] = Field(default_factory=dict)


class EnqueuedTaskResponse(BaseModel):
    """Response containing one queued task id."""

    task_id: str
    queue: str


class DailyShortsScheduleResponse(BaseModel):
    """Response from scheduling a daily batch."""

    task_id: str
    queue: str


class QueueInspectionResponse(BaseModel):
    """Queue state and worker inspection response."""

    active: dict[str, Any]
    reserved: dict[str, Any]
    scheduled: dict[str, Any]
    stats: dict[str, Any]
    queue_lengths: dict[str, int]


class TaskStatusResponse(BaseModel):
    """Celery task status response."""

    task_id: str
    state: str
    ready: bool
    successful: bool
    failed: bool
    result: Any | None = None
    info: Any | None = None


class RevokeTaskResponse(BaseModel):
    """Task revoke response."""

    task_id: str
    revoked: bool
    terminate: bool


class PurgeQueueResponse(BaseModel):
    """Queue purge response."""

    queue: str
    purged: bool
