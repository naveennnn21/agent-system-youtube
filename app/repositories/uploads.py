"""Upload repository."""

from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Upload
from app.models.enums import UploadPlatform, UploadStatus
from app.repositories.base import AsyncRepository


class UploadsRepository(AsyncRepository[Upload]):
    """CRUD and query helpers for uploads."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Upload)

    async def get_by_external_id(
        self,
        platform: UploadPlatform,
        external_video_id: str,
    ) -> Upload | None:
        statement = select(Upload).where(
            Upload.platform == platform,
            Upload.external_video_id == external_video_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_video(
        self,
        video_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Upload]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Upload.video_id == video_id,),
            order_by=desc(Upload.created_at),
        )

    async def list_by_status(
        self,
        status: UploadStatus,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Upload]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Upload.status == status,),
            order_by=desc(Upload.created_at),
        )

    async def list_successful_youtube_uploads(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Upload]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(
                Upload.platform == UploadPlatform.YOUTUBE_SHORTS,
                Upload.status == UploadStatus.SUCCEEDED,
                Upload.external_video_id.is_not(None),
            ),
            order_by=desc(Upload.uploaded_at),
        )
