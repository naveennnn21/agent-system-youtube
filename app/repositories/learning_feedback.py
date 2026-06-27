"""Learning feedback repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LearningFeedback
from app.models.enums import FeedbackType
from app.repositories.base import AsyncRepository


class LearningFeedbackRepository(AsyncRepository[LearningFeedback]):
    """CRUD and query helpers for learning feedback."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LearningFeedback)

    async def list_for_video(
        self,
        video_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[LearningFeedback]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(LearningFeedback.video_id == video_id,),
            order_by=desc(LearningFeedback.created_at),
        )

    async def list_by_type(
        self,
        feedback_type: FeedbackType,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[LearningFeedback]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(LearningFeedback.feedback_type == feedback_type,),
            order_by=desc(LearningFeedback.created_at),
        )

    async def list_unapplied(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[LearningFeedback]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters=(LearningFeedback.applied.is_(False),),
            order_by=desc(LearningFeedback.created_at),
        )

    async def mark_applied(
        self,
        feedback: LearningFeedback,
        *,
        reviewed_at: datetime | None = None,
    ) -> LearningFeedback:
        return await self.update(
            feedback,
            applied=True,
            reviewed_at=reviewed_at or datetime.now(UTC),
        )
