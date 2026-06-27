"""Topic repository."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Topic
from app.models.enums import TopicStatus
from app.repositories.base import AsyncRepository


class TopicsRepository(AsyncRepository[Topic]):
    """CRUD and query helpers for topics."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Topic)

    async def get_by_slug(self, slug: str) -> Topic | None:
        result = await self.session.execute(select(Topic).where(Topic.slug == slug))
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        status: TopicStatus,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Topic]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Topic.status == status,),
            order_by=desc(Topic.priority_score),
        )

    async def search(
        self,
        term: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Topic]:
        pattern = f"%{term}%"
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(Topic.title.ilike(pattern),),
            order_by=desc(Topic.discovered_at),
        )
