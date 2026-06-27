"""Script repository."""

from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Script
from app.models.enums import ScriptStatus
from app.repositories.base import AsyncRepository


class ScriptsRepository(AsyncRepository[Script]):
    """CRUD and query helpers for scripts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Script)

    async def get_latest_for_topic(self, topic_id: uuid.UUID) -> Script | None:
        statement = (
            select(Script)
            .where(Script.topic_id == topic_id)
            .order_by(desc(Script.version), desc(Script.created_at))
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
    ) -> list[Script]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Script.video_id == video_id,),
            order_by=desc(Script.version),
        )

    async def list_by_status(
        self,
        status: ScriptStatus,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Script]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Script.status == status,),
            order_by=desc(Script.created_at),
        )
