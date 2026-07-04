"""Automation and queue management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.automation.queue_manager import QueueManager
from app.automation.tasks import (
    collect_analytics_task,
    dispatch_daily_shorts_task,
    generate_short_task,
    run_learning_task,
)
from app.core.config import get_settings
from app.schemas.automation import (
    DailyShortsRequest,
    DailyShortsScheduleResponse,
    EnqueueShortRequest,
    EnqueuedTaskResponse,
    PurgeQueueResponse,
    QueueInspectionResponse,
    RevokeTaskResponse,
    TaskStatusResponse,
)

router = APIRouter(prefix="/automation", tags=["automation"])


@router.post("/shorts", response_model=EnqueuedTaskResponse)
def enqueue_short(payload: EnqueueShortRequest) -> dict[str, str]:
    """Enqueue one full Short generation workflow."""
    settings = get_settings()
    result = generate_short_task.apply_async(
        kwargs={"metadata": payload.metadata},
        queue=settings.AUTOMATION_SHORTS_QUEUE,
    )
    return {"task_id": result.id, "queue": settings.AUTOMATION_SHORTS_QUEUE}


@router.post("/daily-shorts", response_model=DailyShortsScheduleResponse)
def enqueue_daily_shorts(payload: DailyShortsRequest) -> dict[str, str]:
    """Enqueue the dispatcher that schedules the configured daily Short batch."""
    settings = get_settings()
    result = dispatch_daily_shorts_task.apply_async(
        kwargs={
            "count": payload.count,
            "category": payload.category,
            "base_metadata": payload.base_metadata,
        },
        queue=settings.AUTOMATION_AUTOSTART_QUEUE,
    )
    return {"task_id": result.id, "queue": settings.AUTOMATION_AUTOSTART_QUEUE}


@router.post("/analytics", response_model=EnqueuedTaskResponse)
def enqueue_analytics_collection(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict[str, str]:
    """Enqueue analytics collection as a background job."""
    settings = get_settings()
    result = collect_analytics_task.apply_async(
        kwargs={"start_date": start_date, "end_date": end_date},
        queue=settings.AUTOMATION_ANALYTICS_QUEUE,
    )
    return {"task_id": result.id, "queue": settings.AUTOMATION_ANALYTICS_QUEUE}


@router.post("/learning", response_model=EnqueuedTaskResponse)
def enqueue_learning() -> dict[str, str]:
    """Enqueue a learning-agent run as a background job."""
    settings = get_settings()
    result = run_learning_task.apply_async(
        queue=settings.AUTOMATION_ANALYTICS_QUEUE,
    )
    return {"task_id": result.id, "queue": settings.AUTOMATION_ANALYTICS_QUEUE}


@router.get("/queues", response_model=QueueInspectionResponse)
def inspect_queues() -> dict:
    """Inspect worker activity, scheduled jobs, and Redis queue lengths."""
    return QueueManager().inspect()


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def task_status(task_id: str) -> dict:
    """Return Celery result backend status for one task."""
    return QueueManager().task_status(task_id)


@router.post("/tasks/{task_id}/revoke", response_model=RevokeTaskResponse)
def revoke_task(
    task_id: str,
    terminate: bool = Query(default=False),
) -> dict:
    """Revoke a queued or running task."""
    return QueueManager().revoke(task_id, terminate=terminate)


@router.delete("/queues/{queue_name}", response_model=PurgeQueueResponse)
def purge_queue(queue_name: str) -> dict:
    """Purge pending messages from one known automation queue."""
    try:
        return QueueManager().purge_queue(queue_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
