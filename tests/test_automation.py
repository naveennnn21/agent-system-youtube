from __future__ import annotations

import httpx
import pytest

from app.automation.celery_app import celery_app
from app.automation.notifications import NotificationEvent, NotificationService
from app.automation.queue_manager import QueueManager
from app.automation.scheduler import build_daily_short_payloads, schedule_daily_shorts
from app.core.config import Settings
from app.schemas.automation import EnqueuedTaskResponse, QueueInspectionResponse

pytestmark = pytest.mark.no_db


def test_celery_app_routes_and_beat_schedule_are_configured() -> None:
    schedule = celery_app.conf.beat_schedule
    routes = celery_app.conf.task_routes

    assert schedule["generate-three-shorts-daily"]["task"] == (
        "app.automation.tasks.dispatch_daily_shorts"
    )
    assert schedule["collect-youtube-analytics-daily"]["task"] == (
        "app.automation.tasks.collect_analytics"
    )
    assert schedule["run-learning-daily"]["task"] == "app.automation.tasks.run_learning"
    assert routes["app.automation.tasks.generate_short"]["queue"] == "shorts"
    assert routes["app.automation.tasks.send_notification"]["queue"] == "notifications"
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_track_started is True


def test_daily_short_payloads_generate_three_independent_runs() -> None:
    payloads = build_daily_short_payloads(
        count=3,
        category="technology",
        base_metadata={"audience": "solo creators"},
    )

    assert len(payloads) == 3
    assert [payload["automation_run_index"] for payload in payloads] == [1, 2, 3]
    assert all(payload["automation_batch_size"] == 3 for payload in payloads)
    assert all(payload["category"] == "technology" for payload in payloads)
    assert payloads[0]["filename_prefix"] != payloads[1]["filename_prefix"]
    assert all(payload["audience"] == "solo creators" for payload in payloads)


def test_schedule_daily_shorts_uses_spacing_and_returns_task_ids() -> None:
    enqueued: list[tuple[dict, int]] = []

    def enqueue(metadata: dict, countdown: int) -> str:
        enqueued.append((metadata, countdown))
        return f"task-{len(enqueued)}"

    result = schedule_daily_shorts(
        enqueue=enqueue,
        count=3,
        category="technology",
        spacing_minutes=20,
    )

    assert result["scheduled_count"] == 3
    assert [task["task_id"] for task in result["tasks"]] == [
        "task-1",
        "task-2",
        "task-3",
    ]
    assert [countdown for _, countdown in enqueued] == [0, 1200, 2400]


def test_notification_service_skips_when_disabled() -> None:
    service = NotificationService(
        settings=Settings(NOTIFICATIONS_ENABLED=False),
    )

    result = service.send(
        NotificationEvent(
            event_type="short_generation",
            status="started",
            message="Started",
            task_id="task-id",
        )
    )

    assert result["delivered"] is False
    assert result["reason"] == "notifications disabled"


def test_notification_service_posts_webhook_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = request.read()
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = NotificationService(
        settings=Settings(
            NOTIFICATION_WEBHOOK_URL="https://notify.example.test/webhook",
            NOTIFICATIONS_ENABLED=True,
        ),
        client=client,
    )

    result = service.send(
        NotificationEvent(
            event_type="daily_shorts_dispatch",
            status="scheduled",
            message="Scheduled 3 jobs",
            metadata={"scheduled_count": 3},
        )
    )

    assert result["delivered"] is True
    assert result["status_code"] == 204
    assert captured["url"] == "https://notify.example.test/webhook"
    assert b"daily_shorts_dispatch" in captured["payload"]


def test_queue_manager_inspects_lengths_and_purges_known_queue() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.lengths = {
                "automation": 1,
                "shorts": 2,
                "analytics": 0,
                "notifications": 3,
            }
            self.deleted: list[str] = []

        def llen(self, queue_name: str) -> int:
            return self.lengths.get(queue_name, 0)

        def delete(self, queue_name: str) -> int:
            self.deleted.append(queue_name)
            return 1

    class FakeInspector:
        def active(self):
            return {"worker": []}

        def reserved(self):
            return {"worker": []}

        def scheduled(self):
            return {"worker": []}

        def stats(self):
            return {"worker": {"ok": True}}

    class FakeControl:
        def inspect(self, timeout: int = 2):
            return FakeInspector()

    class FakeApp:
        control = FakeControl()

    redis = FakeRedis()
    manager = QueueManager(
        app=FakeApp(),
        redis_client=redis,
        settings=Settings(),
    )

    inspected = manager.inspect()
    purged = manager.purge_queue("shorts")

    assert inspected["queue_lengths"]["shorts"] == 2
    assert inspected["stats"]["worker"]["ok"] is True
    assert purged == {"queue": "shorts", "purged": True}
    assert redis.deleted == ["shorts"]
    with pytest.raises(ValueError):
        manager.purge_queue("unknown")


def test_automation_schemas_accept_public_contracts() -> None:
    task = EnqueuedTaskResponse.model_validate({"task_id": "abc", "queue": "shorts"})
    queues = QueueInspectionResponse.model_validate(
        {
            "active": {},
            "reserved": {},
            "scheduled": {},
            "stats": {},
            "queue_lengths": {"shorts": 2},
        }
    )

    assert task.queue == "shorts"
    assert queues.queue_lengths["shorts"] == 2
