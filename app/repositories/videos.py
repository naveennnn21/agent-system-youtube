"""Video repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Video
from app.models.enums import VideoStatus
from app.repositories.base import AsyncRepository


class VideosRepository(AsyncRepository[Video]):
    """CRUD and query helpers for videos."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Video)

    async def list_by_topic(
        self,
        topic_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Video]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Video.topic_id == topic_id,),
            order_by=desc(Video.created_at),
        )

    async def list_by_status(
        self,
        status: VideoStatus,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Video]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Video.status == status,),
            order_by=desc(Video.created_at),
        )

    async def mark_published(
        self,
        video: Video,
        *,
        published_at: datetime | None = None,
    ) -> Video:
        return await self.update(
            video,
            status=VideoStatus.PUBLISHED,
            published_at=published_at or datetime.now(UTC),
        )
