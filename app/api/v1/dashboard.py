"""Read-only dashboard endpoints."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.queue_manager import QueueManager
from app.db.session import get_db
from app.models import Analytics, LearningFeedback, Upload, Video
from app.models.enums import UploadStatus, VideoStatus
from app.schemas.dashboard import (
    DashboardAgentLogResponse,
    DashboardLearningInsightResponse,
    DashboardOverviewResponse,
    DashboardQueueResponse,
    DashboardUploadResponse,
    DashboardVideoResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
async def overview(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return dashboard count cards and analytics trend series."""
    start_date = date.today() - timedelta(days=days - 1)
    total_videos = await _count(session, Video)
    published_videos = await _count(
        session,
        Video,
        Video.status == VideoStatus.PUBLISHED,
    )
    failed_videos = await _count(session, Video, Video.status == VideoStatus.FAILED)
    pending_uploads = await _count(
        session,
        Upload,
        Upload.status.in_(
            [
                UploadStatus.PENDING,
                UploadStatus.UPLOADING,
                UploadStatus.RETRYING,
            ]
        ),
    )
    totals = await session.execute(
        select(
            func.coalesce(func.sum(Analytics.views), 0),
            func.coalesce(func.sum(Analytics.watch_time_seconds), 0),
            func.avg(Analytics.click_through_rate),
            func.avg(Analytics.retention_rate),
            func.coalesce(func.sum(Analytics.subscribers_gained), 0),
        )
    )
    total_views, total_watch_time, average_ctr, average_retention, subscribers = (
        totals.one()
    )

    return {
        "metrics": [
            {
                "label": "Videos",
                "value": total_videos,
                "detail": f"{published_videos} published",
            },
            {
                "label": "Views",
                "value": int(total_views or 0),
                "detail": "All stored analytics snapshots",
            },
            {
                "label": "Watch Time",
                "value": int(total_watch_time or 0),
                "detail": "Seconds watched",
            },
            {
                "label": "Avg CTR",
                "value": _float_or_none(average_ctr),
                "detail": "Stored snapshot average",
            },
            {
                "label": "Avg Retention",
                "value": _float_or_none(average_retention),
                "detail": "Stored snapshot average",
            },
            {
                "label": "Subscribers",
                "value": int(subscribers or 0),
                "detail": "Net gained from snapshots",
            },
            {
                "label": "Pending Uploads",
                "value": pending_uploads,
                "detail": "Queued, uploading, or retrying",
            },
            {
                "label": "Failures",
                "value": failed_videos,
                "detail": "Videos marked failed",
            },
        ],
        "video_status_counts": await _status_counts(session, Video.status),
        "upload_status_counts": await _status_counts(session, Upload.status),
        "trend": await _analytics_trend(session, start_date=start_date),
    }


@router.get("/videos", response_model=list[DashboardVideoResponse])
async def videos(
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return recent videos with latest stored analytics metrics."""
    result = await session.execute(
        select(Video).order_by(desc(Video.created_at)).limit(limit)
    )
    records = list(result.scalars().all())
    latest_metrics = await _latest_metrics_for_videos(
        session,
        [video.id for video in records],
    )
    return [_video_response(video, latest_metrics.get(video.id)) for video in records]


@router.get("/uploads", response_model=list[DashboardUploadResponse])
async def uploads(
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return recent upload attempts and their current status."""
    result = await session.execute(
        select(Upload, Video.title)
        .join(Video, Video.id == Upload.video_id)
        .order_by(desc(Upload.created_at))
        .limit(limit)
    )
    return [_upload_response(upload, title) for upload, title in result.all()]


@router.get("/agent-logs", response_model=DashboardQueueResponse)
async def agent_logs(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return queue activity and recent failure events as dashboard logs."""
    queue_lengths: dict[str, int] = {}
    logs: list[dict[str, Any]] = []
    try:
        inspection = QueueManager().inspect()
        queue_lengths = dict(inspection.get("queue_lengths") or {})
        logs.extend(_queue_logs_from_inspection(inspection))
    except Exception as exc:
        logs.append(
            {
                "id": "queue-inspection-error",
                "level": "error",
                "source": "celery",
                "message": f"Queue inspection failed: {exc}",
                "status": "failed",
                "metadata": {},
            }
        )

    failed_uploads = await session.execute(
        select(Upload, Video.title)
        .join(Video, Video.id == Upload.video_id)
        .where(Upload.status == UploadStatus.FAILED)
        .order_by(desc(Upload.created_at))
        .limit(limit)
    )
    for upload, title in failed_uploads.all():
        logs.append(
            {
                "id": f"upload-{upload.id}",
                "level": "error",
                "source": "youtube_upload",
                "message": upload.error_message or f"Upload failed for {title}.",
                "queue": "shorts",
                "status": upload.status.value,
                "created_at": upload.created_at,
                "metadata": {
                    "upload_id": str(upload.id),
                    "video_id": str(upload.video_id),
                    "video_title": title,
                },
            }
        )

    return {"queue_lengths": queue_lengths, "logs": logs[:limit]}


@router.get(
    "/learning-insights",
    response_model=list[DashboardLearningInsightResponse],
)
async def learning_insights(
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return recent learning recommendations and whether they were applied."""
    result = await session.execute(
        select(LearningFeedback, Video.title)
        .outerjoin(Video, Video.id == LearningFeedback.video_id)
        .order_by(desc(LearningFeedback.created_at))
        .limit(limit)
    )
    return [_learning_response(feedback, title) for feedback, title in result.all()]


async def _count(
    session: AsyncSession,
    model: type,
    *filters: Any,
) -> int:
    statement = select(func.count()).select_from(model)
    for criterion in filters:
        statement = statement.where(criterion)
    value = await session.scalar(statement)
    return int(value or 0)


async def _status_counts(session: AsyncSession, column: Any) -> dict[str, int]:
    result = await session.execute(select(column, func.count()).group_by(column))
    return {str(status.value): int(count) for status, count in result.all()}


async def _analytics_trend(
    session: AsyncSession,
    *,
    start_date: date,
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(
            Analytics.snapshot_date,
            func.coalesce(func.sum(Analytics.views), 0),
            func.coalesce(func.sum(Analytics.watch_time_seconds), 0),
            func.avg(Analytics.click_through_rate),
            func.avg(Analytics.retention_rate),
        )
        .where(Analytics.snapshot_date >= start_date)
        .group_by(Analytics.snapshot_date)
        .order_by(Analytics.snapshot_date)
    )
    return [
        {
            "date": snapshot_date,
            "views": int(views or 0),
            "watch_time_seconds": int(watch_time or 0),
            "average_ctr": _float_or_none(ctr),
            "average_retention": _float_or_none(retention),
        }
        for snapshot_date, views, watch_time, ctr, retention in result.all()
    ]


async def _latest_metrics_for_videos(
    session: AsyncSession,
    video_ids: list[Any],
) -> dict[Any, Analytics]:
    if not video_ids:
        return {}
    latest_snapshot = (
        select(
            Analytics.video_id.label("video_id"),
            func.max(Analytics.snapshot_date).label("snapshot_date"),
        )
        .where(Analytics.video_id.in_(video_ids))
        .group_by(Analytics.video_id)
        .subquery()
    )
    result = await session.execute(
        select(Analytics).join(
            latest_snapshot,
            and_(
                Analytics.video_id == latest_snapshot.c.video_id,
                Analytics.snapshot_date == latest_snapshot.c.snapshot_date,
            ),
        )
    )
    return {record.video_id: record for record in result.scalars().all()}


def _video_response(video: Video, metrics: Analytics | None) -> dict[str, Any]:
    return {
        "id": str(video.id),
        "title": video.title,
        "status": video.status.value,
        "duration_seconds": video.duration_seconds,
        "file_path": video.file_path,
        "thumbnail_path": video.thumbnail_path,
        "scheduled_at": video.scheduled_at,
        "published_at": video.published_at,
        "created_at": video.created_at,
        "latest_views": int(metrics.views) if metrics else 0,
        "latest_retention_rate": _float_or_none(metrics.retention_rate if metrics else None),
        "latest_ctr": _float_or_none(metrics.click_through_rate if metrics else None),
    }


def _upload_response(upload: Upload, video_title: str | None) -> dict[str, Any]:
    return {
        "id": str(upload.id),
        "video_id": str(upload.video_id),
        "video_title": video_title,
        "platform": upload.platform.value,
        "external_video_id": upload.external_video_id,
        "upload_url": upload.upload_url,
        "status": upload.status.value,
        "privacy_status": upload.privacy_status,
        "error_message": upload.error_message,
        "started_at": upload.started_at,
        "uploaded_at": upload.uploaded_at,
        "created_at": upload.created_at,
    }


def _learning_response(
    feedback: LearningFeedback,
    video_title: str | None,
) -> dict[str, Any]:
    return {
        "id": str(feedback.id),
        "feedback_type": feedback.feedback_type.value,
        "signal": feedback.signal,
        "score": _float_or_none(feedback.score),
        "notes": feedback.notes,
        "recommendations": feedback.recommendations,
        "applied": feedback.applied,
        "model_version": feedback.model_version,
        "created_at": feedback.created_at,
        "reviewed_at": feedback.reviewed_at,
        "video_id": str(feedback.video_id) if feedback.video_id else None,
        "video_title": video_title,
    }


def _queue_logs_from_inspection(inspection: dict[str, Any]) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for state in ("active", "reserved", "scheduled"):
        workers = inspection.get(state) or {}
        for worker, tasks in workers.items():
            for task in tasks or []:
                task_id = str(task.get("id") or task.get("request", {}).get("id") or "")
                name = str(task.get("name") or task.get("request", {}).get("name") or "task")
                queue = _task_queue(task)
                logs.append(
                    {
                        "id": f"{state}-{task_id or len(logs)}",
                        "level": "info",
                        "source": worker,
                        "message": f"{name} is {state}.",
                        "queue": queue,
                        "task_id": task_id or None,
                        "status": state,
                        "created_at": now,
                        "metadata": task,
                    }
                )
    if not logs:
        logs.append(
            {
                "id": "queues-idle",
                "level": "info",
                "source": "celery",
                "message": "No active, reserved, or scheduled Celery tasks.",
                "status": "idle",
                "created_at": now,
                "metadata": {},
            }
        )
    return logs


def _task_queue(task: dict[str, Any]) -> str | None:
    delivery_info = task.get("delivery_info") or task.get("request", {}).get("delivery_info") or {}
    queue = delivery_info.get("routing_key") or delivery_info.get("exchange")
    return str(queue) if queue else None


def _float_or_none(value: Decimal | float | int | None) -> float | None:
    return float(value) if value is not None else None
