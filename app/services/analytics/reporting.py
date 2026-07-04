"""Reporting helpers for stored analytics snapshots."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.models import Analytics
from app.services.analytics.models import AnalyticsReport


class AnalyticsReporter:
    """Build aggregate reports from stored analytics rows."""

    def build_report(
        self,
        records: list[Analytics],
        *,
        start_date: date,
        end_date: date,
        top_n: int = 10,
    ) -> AnalyticsReport:
        total_views = sum(record.views for record in records)
        total_watch_time = sum(record.watch_time_seconds for record in records)
        subscribers = sum(record.subscribers_gained for record in records)
        top_videos = [
            _record_summary(record)
            for record in sorted(records, key=lambda item: item.views, reverse=True)[:top_n]
        ]
        daily_totals = _daily_totals(records)

        return AnalyticsReport(
            start_date=start_date,
            end_date=end_date,
            video_count=len({record.video_id for record in records}),
            total_views=total_views,
            total_watch_time_seconds=total_watch_time,
            average_ctr=_weighted_average(records, "click_through_rate"),
            average_retention=_weighted_average(records, "retention_rate"),
            subscribers_gained=subscribers,
            top_videos=top_videos,
            daily_totals=daily_totals,
        )


def _weighted_average(records: list[Analytics], field: str) -> float | None:
    weighted_total = 0.0
    weight = 0
    for record in records:
        value = getattr(record, field)
        if value is None:
            continue
        views = max(record.views, 1)
        weighted_total += float(value) * views
        weight += views
    if weight == 0:
        return None
    return round(weighted_total / weight, 4)


def _daily_totals(records: list[Analytics]) -> list[dict[str, Any]]:
    grouped: dict[date, dict[str, Any]] = defaultdict(
        lambda: {
            "views": 0,
            "watch_time_seconds": 0,
            "subscribers_gained": 0,
        }
    )
    for record in records:
        bucket = grouped[record.snapshot_date]
        bucket["views"] += record.views
        bucket["watch_time_seconds"] += record.watch_time_seconds
        bucket["subscribers_gained"] += record.subscribers_gained
    return [
        {"date": day.isoformat(), **values}
        for day, values in sorted(grouped.items(), key=lambda item: item[0])
    ]


def _record_summary(record: Analytics) -> dict[str, Any]:
    return {
        "analytics_id": str(record.id),
        "video_id": str(record.video_id),
        "upload_id": str(record.upload_id) if record.upload_id else None,
        "snapshot_date": record.snapshot_date.isoformat(),
        "views": record.views,
        "watch_time_seconds": record.watch_time_seconds,
        "click_through_rate": float(record.click_through_rate) if record.click_through_rate is not None else None,
        "retention_rate": float(record.retention_rate) if record.retention_rate is not None else None,
        "subscribers_gained": record.subscribers_gained,
    }
