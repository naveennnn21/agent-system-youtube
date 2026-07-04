"""Queue inspection and management helpers for Celery/Redis."""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.result import AsyncResult
from redis import Redis

from app.automation.celery_app import celery_app
from app.core.config import Settings, get_settings


class QueueManager:
    """Inspect queues, task states, and revoke/purge jobs."""

    def __init__(
        self,
        *,
        app: Celery | None = None,
        redis_client: Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.app = app or celery_app
        self.redis = redis_client or Redis.from_url(self.settings.CELERY_BROKER_URL)

    def queue_lengths(self) -> dict[str, int]:
        return {
            queue_name: int(self.redis.llen(queue_name))
            for queue_name in self.settings.AUTOMATION_QUEUE_NAMES
        }

    def inspect(self) -> dict[str, Any]:
        inspector = self.app.control.inspect(timeout=2)
        return {
            "active": inspector.active() or {},
            "reserved": inspector.reserved() or {},
            "scheduled": inspector.scheduled() or {},
            "stats": inspector.stats() or {},
            "queue_lengths": self.queue_lengths(),
        }

    def task_status(self, task_id: str) -> dict[str, Any]:
        result = AsyncResult(task_id, app=self.app)
        payload = {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else False,
            "failed": result.failed() if result.ready() else False,
        }
        if result.ready():
            payload["result"] = _safe_result(result.result)
        else:
            payload["info"] = _safe_result(result.info)
        return payload

    def revoke(self, task_id: str, *, terminate: bool = False) -> dict[str, Any]:
        self.app.control.revoke(task_id, terminate=terminate)
        return {"task_id": task_id, "revoked": True, "terminate": terminate}

    def purge_queue(self, queue_name: str) -> dict[str, Any]:
        if queue_name not in self.settings.AUTOMATION_QUEUE_NAMES:
            raise ValueError(f"Unknown queue: {queue_name}")
        removed = int(self.redis.delete(queue_name))
        return {"queue": queue_name, "purged": bool(removed)}


def _safe_result(value: Any) -> Any:
    if isinstance(value, Exception):
        return {"error": str(value), "type": value.__class__.__name__}
    return value
