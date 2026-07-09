"""Reusable analytics collection jobs."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analytics import AnalyticsAgent
from app.core.config import Settings, get_settings
from app.services.analytics import AnalyticsCollectionRequest


async def collect_youtube_analytics_job(
    session: AsyncSession,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    settings: Settings | None = None,
) -> dict:
    """Collect YouTube Analytics metrics for successful uploads.

    This function is scheduler-agnostic. It can be called from Celery, APScheduler,
    a cron-triggered command, or an internal admin endpoint.
    """
    settings = settings or get_settings()
    end = end_date or (date.today() - timedelta(days=1))
    start = start_date or (
        end - timedelta(days=settings.YOUTUBE_ANALYTICS_LOOKBACK_DAYS)
    )
    agent = AnalyticsAgent.from_session(session, settings)
    result = await agent.collect(
        AnalyticsCollectionRequest(
            start_date=start,
            end_date=end,
            max_results=settings.YOUTUBE_ANALYTICS_COLLECTION_LIMIT,
            metrics=settings.YOUTUBE_ANALYTICS_METRICS,
        )
    )
    return result.to_dict()
