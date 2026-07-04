"""Celery tasks for scheduled Shorts automation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from celery import Task
from langchain_core.messages import BaseMessage

import app.db.session as db_session
from app.agents.learning import LearningAgent
from app.agents.workflow import create_shorts_workflow_graph
from app.automation.celery_app import celery_app
from app.automation.notifications import NotificationEvent, NotificationService
from app.automation.scheduler import schedule_daily_shorts
from app.core.config import get_settings
from app.jobs.analytics import collect_youtube_analytics_job
from app.services.learning import LearningAnalysisRequest

logger = logging.getLogger(__name__)
settings = get_settings()


class RetriableTask(Task):
    """Base task with production retry defaults."""

    autoretry_for = (Exception,)
    max_retries = settings.CELERY_TASK_MAX_RETRIES
    retry_backoff = settings.CELERY_TASK_RETRY_BACKOFF
    retry_backoff_max = settings.CELERY_TASK_RETRY_BACKOFF_MAX
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=RetriableTask,
    name="app.automation.tasks.dispatch_daily_shorts",
)
def dispatch_daily_shorts_task(
    self,
    *,
    count: int | None = None,
    category: str | None = None,
    base_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Schedule the daily batch of Shorts generation jobs."""
    settings = get_settings()
    daily_count = count or settings.AUTOMATION_DAILY_SHORTS_COUNT
    daily_category = category or settings.AUTOMATION_DEFAULT_CATEGORY

    def enqueue(metadata: dict[str, Any], countdown: int) -> str:
        result = generate_short_task.apply_async(
            kwargs={"metadata": metadata},
            countdown=countdown,
            queue=settings.AUTOMATION_SHORTS_QUEUE,
        )
        return result.id

    scheduled = schedule_daily_shorts(
        enqueue=enqueue,
        count=daily_count,
        category=daily_category,
        spacing_minutes=settings.AUTOMATION_SHORT_SPACING_MINUTES,
        base_metadata=base_metadata,
    )
    _enqueue_notification(
        NotificationEvent(
            event_type="daily_shorts_dispatch",
            status="scheduled",
            message=f"Scheduled {scheduled['scheduled_count']} Shorts generation jobs.",
            task_id=self.request.id,
            metadata=scheduled,
        )
    )
    return scheduled


@celery_app.task(
    bind=True,
    base=RetriableTask,
    name="app.automation.tasks.generate_short",
)
def generate_short_task(
    self,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate, upload, analyze, and learn from one Short workflow."""
    metadata = dict(metadata or {})
    metadata.setdefault("automation_task_id", self.request.id)
    _enqueue_notification(
        NotificationEvent(
            event_type="short_generation",
            status="started",
            message="Short generation workflow started.",
            task_id=self.request.id,
            metadata=_public_metadata(metadata),
        )
    )
    try:
        result = asyncio.run(_run_workflow(metadata))
    except Exception as exc:
        _enqueue_notification(
            NotificationEvent(
                event_type="short_generation",
                status="failed",
                message=str(exc),
                task_id=self.request.id,
                metadata=_public_metadata(metadata),
            )
        )
        raise

    if result.get("workflow_status") == "failed":
        error_message = _workflow_error_message(result)
        _enqueue_notification(
            NotificationEvent(
                event_type="short_generation",
                status="failed",
                message=error_message,
                task_id=self.request.id,
                metadata={"workflow": result},
            )
        )
        raise RuntimeError(error_message)

    _enqueue_notification(
        NotificationEvent(
            event_type="short_generation",
            status="succeeded",
            message="Short generation workflow completed.",
            task_id=self.request.id,
            metadata={
                "upload_result": result.get("upload_result"),
                "learning_confidence": (
                    result.get("learning_result", {})
                    .get("recommendations", {})
                    .get("confidence")
                ),
            },
        )
    )
    return result


@celery_app.task(
    bind=True,
    base=RetriableTask,
    name="app.automation.tasks.collect_analytics",
)
def collect_analytics_task(
    self,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Collect YouTube Analytics metrics for successful uploads."""
    result = asyncio.run(
        _run_analytics_collection(
            start_date=_date_or_none(start_date),
            end_date=_date_or_none(end_date),
        )
    )
    _enqueue_notification(
        NotificationEvent(
            event_type="analytics_collection",
            status="succeeded",
            message=f"Stored {result.get('stored_count', 0)} analytics snapshots.",
            task_id=self.request.id,
            metadata=result,
        )
    )
    return result


@celery_app.task(
    bind=True,
    base=RetriableTask,
    name="app.automation.tasks.run_learning",
)
def run_learning_task(self) -> dict[str, Any]:
    """Run the learning agent against stored analytics."""
    result = asyncio.run(_run_learning())
    _enqueue_notification(
        NotificationEvent(
            event_type="learning",
            status="succeeded",
            message=f"Learning completed from {result.get('sample_count', 0)} samples.",
            task_id=self.request.id,
            metadata=result,
        )
    )
    return result


@celery_app.task(
    bind=True,
    name="app.automation.tasks.send_notification",
    queue=get_settings().AUTOMATION_NOTIFICATIONS_QUEUE,
)
def send_notification_task(self, event: dict[str, Any]) -> dict[str, Any]:
    """Deliver an automation notification."""
    return NotificationService().send(
        NotificationEvent(
            event_type=str(event.get("event_type", "automation")),
            status=str(event.get("status", "info")),
            message=str(event.get("message", "")),
            task_id=event.get("task_id"),
            metadata=dict(event.get("metadata") or {}),
            created_at=str(event.get("created_at") or datetime.utcnow().isoformat()),
        )
    )


async def _run_workflow(metadata: dict[str, Any]) -> dict[str, Any]:
    await db_session.init_db()
    try:
        if db_session.AsyncSessionLocal is None:
            raise RuntimeError("Database session factory was not initialised.")
        async with db_session.AsyncSessionLocal() as session:
            workflow_metadata = dict(metadata)
            workflow_metadata["db_session"] = session
            graph = create_shorts_workflow_graph()
            result = await graph.ainvoke(
                {
                    "metadata": workflow_metadata,
                    "messages": [],
                    "workflow_status": "running",
                    "errors": [],
                    "monitoring": [],
                }
            )
            if result.get("workflow_status") == "failed":
                await session.rollback()
            else:
                await session.commit()
            return _json_safe(_without_runtime_metadata(result))
    finally:
        await db_session.close_db()


async def _run_analytics_collection(
    *,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    await db_session.init_db()
    try:
        if db_session.AsyncSessionLocal is None:
            raise RuntimeError("Database session factory was not initialised.")
        async with db_session.AsyncSessionLocal() as session:
            result = await collect_youtube_analytics_job(
                session,
                start_date=start_date,
                end_date=end_date,
            )
            await session.commit()
            return _json_safe(result)
    finally:
        await db_session.close_db()


async def _run_learning() -> dict[str, Any]:
    await db_session.init_db()
    try:
        if db_session.AsyncSessionLocal is None:
            raise RuntimeError("Database session factory was not initialised.")
        async with db_session.AsyncSessionLocal() as session:
            agent = LearningAgent.from_session(session)
            result = await agent.run_learning_cycle(
                LearningAnalysisRequest(store_results=True)
            )
            await session.commit()
            return _json_safe(result.to_dict())
    finally:
        await db_session.close_db()


def _enqueue_notification(event: NotificationEvent) -> None:
    try:
        send_notification_task.apply_async(
            args=[event.to_dict()],
            queue=get_settings().AUTOMATION_NOTIFICATIONS_QUEUE,
        )
    except Exception as exc:
        logger.warning("failed to enqueue notification: %s", exc)


def _workflow_error_message(result: dict[str, Any]) -> str:
    errors = result.get("errors") or []
    if errors:
        latest = errors[-1]
        return f"{latest.get('step', 'workflow')} failed: {latest.get('error', 'unknown error')}"
    return "Short workflow failed."


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in metadata.items()
        if key != "db_session" and not key.endswith("_agent")
    }


def _without_runtime_metadata(result: dict[str, Any]) -> dict[str, Any]:
    payload = dict(result)
    if "metadata" in payload and isinstance(payload["metadata"], dict):
        payload["metadata"] = _public_metadata(payload["metadata"])
    return payload


def _date_or_none(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, BaseMessage):
        return {"type": value.type, "content": value.content}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, uuid.UUID)):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
