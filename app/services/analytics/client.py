"""YouTube Analytics API v2 client."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.services.analytics.models import AnalyticsSnapshot, YouTubeAnalyticsQuery
from app.services.youtube.oauth import GoogleOAuthClient


class YouTubeAnalyticsError(RuntimeError):
    """Raised when YouTube Analytics collection fails."""


class YouTubeAnalyticsClient:
    """Fetch video analytics through YouTube Analytics API reports.query."""

    def __init__(
        self,
        *,
        oauth_client: GoogleOAuthClient,
        base_url: str = "https://youtubeanalytics.googleapis.com/v2",
        timeout: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.oauth_client = oauth_client
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    async def fetch_video_metrics(
        self,
        query: YouTubeAnalyticsQuery,
    ) -> list[AnalyticsSnapshot]:
        token = await self.oauth_client.refresh_access_token()
        headers = {"Authorization": f"{token.token_type} {token.access_token}"}
        try:
            if self._client is not None:
                response = await self._client.get(
                    f"{self.base_url}/reports",
                    params=query.to_params(),
                    headers=headers,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/reports",
                        params=query.to_params(),
                        headers=headers,
                    )
        except httpx.HTTPError as exc:
            raise YouTubeAnalyticsError(f"YouTube Analytics request failed: {exc}") from exc

        if response.status_code >= 400:
            raise YouTubeAnalyticsError(
                f"YouTube Analytics request failed with HTTP {response.status_code}: "
                f"{response.text}"
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise YouTubeAnalyticsError("YouTube Analytics response must be a JSON object.")
        return parse_analytics_response(payload, query=query)


def parse_analytics_response(
    payload: dict[str, Any],
    *,
    query: YouTubeAnalyticsQuery,
) -> list[AnalyticsSnapshot]:
    """Parse YouTube Analytics resultTable JSON into normalized snapshots."""
    headers = [
        header.get("name")
        for header in payload.get("columnHeaders", [])
        if isinstance(header, dict)
    ]
    if not headers:
        return []
    rows = payload.get("rows") or []
    snapshots: list[AnalyticsSnapshot] = []

    for row in rows:
        if not isinstance(row, list):
            continue
        values = dict(zip(headers, row, strict=False))
        external_video_id = str(
            values.get("video")
            or (query.video_ids[0] if len(query.video_ids) == 1 else "")
        )
        if not external_video_id:
            continue
        snapshot_date = _parse_snapshot_date(values.get("day"), query.end_date)
        raw_metrics = {
            key: value
            for key, value in values.items()
            if key not in {"video", "day"}
        }
        snapshots.append(
            AnalyticsSnapshot(
                external_video_id=external_video_id,
                snapshot_date=snapshot_date,
                views=_int_metric(values.get("views")),
                likes=_int_metric(values.get("likes")),
                comments=_int_metric(values.get("comments")),
                shares=_int_metric(values.get("shares")),
                watch_time_seconds=round(
                    _float_metric(values.get("estimatedMinutesWatched")) * 60
                ),
                average_view_duration_seconds=_nullable_float(
                    values.get("averageViewDuration")
                ),
                retention_rate=_percentage_to_rate(
                    values.get("averageViewPercentage")
                ),
                click_through_rate=_first_percentage_to_rate(
                    values,
                    "impressionsClickThroughRate",
                    "annotationClickThroughRate",
                    "cardClickRate",
                ),
                subscribers_gained=_int_metric(values.get("subscribersGained")),
                revenue_estimate=_nullable_float(values.get("estimatedRevenue")),
                raw_metrics=raw_metrics,
            )
        )
    return snapshots


def _parse_snapshot_date(value: Any, fallback: date) -> date:
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return fallback


def _int_metric(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(round(float(value)))


def _float_metric(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _nullable_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _percentage_to_rate(value: Any) -> float | None:
    if value in (None, ""):
        return None
    number = float(value)
    return round(number / 100, 4) if number > 1 else round(number, 4)


def _first_percentage_to_rate(values: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in values and values[key] not in (None, ""):
            return _percentage_to_rate(values[key])
    return None
