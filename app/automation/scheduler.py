"""Scheduling helpers for recurring Shorts automation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any


def build_daily_short_payloads(
    *,
    count: int,
    category: str,
    base_metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build independent workflow metadata payloads for one daily batch."""
    today = datetime.now(UTC).date().isoformat()
    payloads: list[dict[str, Any]] = []
    for index in range(count):
        metadata = dict(base_metadata or {})
        metadata.update(
            {
                "automation_batch_date": today,
                "automation_run_index": index + 1,
                "automation_batch_size": count,
                "category": metadata.get("category", category),
                "filename_prefix": metadata.get(
                    "filename_prefix", f"short-{today}-{index + 1}"
                ),
            }
        )
        payloads.append(metadata)
    return payloads


def schedule_daily_shorts(
    *,
    enqueue: Callable[[dict[str, Any], int], str],
    count: int,
    category: str,
    spacing_minutes: int,
    base_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Schedule daily Short generation jobs and return task ids."""
    payloads = build_daily_short_payloads(
        count=count,
        category=category,
        base_metadata=base_metadata,
    )
    tasks = []
    for index, payload in enumerate(payloads):
        countdown = index * spacing_minutes * 60
        tasks.append(
            {
                "task_id": enqueue(payload, countdown),
                "countdown_seconds": countdown,
                "metadata": payload,
            }
        )
    return {
        "scheduled_count": len(tasks),
        "tasks": tasks,
    }
