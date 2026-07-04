"""Analytics repository."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Analytics, Video
from app.models.enums import UploadPlatform
from app.repositories.base import AsyncRepository


class AnalyticsRepository(AsyncRepository[Analytics]):
    """CRUD and query helpers for analytics snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Analytics)

    async def get_snapshot(
        self,
        video_id: uuid.UUID,
        snapshot_date: date,
        platform: UploadPlatform = UploadPlatform.YOUTUBE_SHORTS,
    ) -> Analytics | None:
        statement = select(Analytics).where(
            Analytics.video_id == video_id,
            Analytics.platform == platform,
            Analytics.snapshot_date == snapshot_date,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def latest_for_video(
        self,
        video_id: uuid.UUID,
        platform: UploadPlatform = UploadPlatform.YOUTUBE_SHORTS,
    ) -> Analytics | None:
        statement = (
            select(Analytics)
            .where(
                Analytics.video_id == video_id,
                Analytics.platform == platform,
            )
            .order_by(desc(Analytics.snapshot_date), desc(Analytics.created_at))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_video(
        self,
        video_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Analytics]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Analytics.video_id == video_id,),
            order_by=desc(Analytics.snapshot_date),
        )

    async def list_between(
        self,
        *,
        start_date: date,
        end_date: date,
        platform: UploadPlatform = UploadPlatform.YOUTUBE_SHORTS,
        offset: int = 0,
        limit: int = 1000,
    ) -> list[Analytics]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(
                Analytics.platform == platform,
                Analytics.snapshot_date >= start_date,
                Analytics.snapshot_date <= end_date,
            ),
            order_by=desc(Analytics.snapshot_date),
        )

    async def list_recent_with_content(
        self,
        *,
        days: int = 90,
        limit: int = 500,
        platform: UploadPlatform = UploadPlatform.YOUTUBE_SHORTS,
    ) -> list[Analytics]:
        """Return recent analytics snapshots with related content loaded."""
        cutoff = date.today() - timedelta(days=max(days, 1))
        statement = (
            select(Analytics)
            .where(
                Analytics.platform == platform,
                Analytics.snapshot_date >= cutoff,
            )
            .options(
                selectinload(Analytics.video).selectinload(Video.topic),
                selectinload(Analytics.video).selectinload(Video.scripts),
                selectinload(Analytics.video).selectinload(Video.uploads),
            )
            .order_by(desc(Analytics.snapshot_date), desc(Analytics.views))
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
