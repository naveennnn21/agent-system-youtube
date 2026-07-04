"""Analytics collection and reporting endpoints."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analytics import AnalyticsAgent
from app.db.session import get_db
from app.repositories import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsCollectionRequestSchema,
    AnalyticsCollectionResponse,
    AnalyticsMetricResponse,
    AnalyticsReportResponse,
)
from app.services.analytics import AnalyticsCollectionRequest, AnalyticsReporter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/collect", response_model=AnalyticsCollectionResponse)
async def collect_analytics(
    payload: AnalyticsCollectionRequestSchema,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Collect YouTube Analytics metrics and store snapshots in PostgreSQL."""
    agent = AnalyticsAgent.from_session(session)
    result = await agent.collect(
        AnalyticsCollectionRequest(
            start_date=payload.start_date,
            end_date=payload.end_date,
            external_video_ids=payload.external_video_ids,
            max_results=payload.max_results,
            metrics=payload.metrics,
        )
    )
    return result.to_dict()


@router.get("/videos/{video_id}", response_model=list[AnalyticsMetricResponse])
async def list_video_analytics(
    video_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List stored analytics snapshots for one internal video id."""
    records = await AnalyticsRepository(session).list_for_video(video_id)
    return [_metric_response(record) for record in records]


@router.get("/report", response_model=AnalyticsReportResponse)
async def analytics_report(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    top_n: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return an aggregate analytics report over stored PostgreSQL metrics."""
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    records = await AnalyticsRepository(session).list_between(
        start_date=start,
        end_date=end,
        limit=5000,
    )
    return AnalyticsReporter().build_report(
        records,
        start_date=start,
        end_date=end,
        top_n=top_n,
    ).to_dict()


@router.get("/top-videos", response_model=list[dict])
async def top_videos(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return top stored videos by views for a date range."""
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    records = await AnalyticsRepository(session).list_between(
        start_date=start,
        end_date=end,
        limit=5000,
    )
    report = AnalyticsReporter().build_report(
        records,
        start_date=start,
        end_date=end,
        top_n=limit,
    )
    return report.top_videos


def _metric_response(record) -> dict:
    return {
        "analytics_id": str(record.id),
        "video_id": str(record.video_id),
        "upload_id": str(record.upload_id) if record.upload_id else None,
        "snapshot_date": record.snapshot_date,
        "views": record.views,
        "likes": record.likes,
        "comments": record.comments,
        "shares": record.shares,
        "watch_time_seconds": record.watch_time_seconds,
        "average_view_duration_seconds": (
            float(record.average_view_duration_seconds)
            if record.average_view_duration_seconds is not None
            else None
        ),
        "retention_rate": (
            float(record.retention_rate)
            if record.retention_rate is not None
            else None
        ),
        "click_through_rate": (
            float(record.click_through_rate)
            if record.click_through_rate is not None
            else None
        ),
        "subscribers_gained": record.subscribers_gained,
        "revenue_estimate": (
            float(record.revenue_estimate)
            if record.revenue_estimate is not None
            else None
        ),
        "raw_metrics": record.raw_metrics,
    }
