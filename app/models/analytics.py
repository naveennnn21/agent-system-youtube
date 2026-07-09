"""Analytics model."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import UploadPlatform, enum_values

if TYPE_CHECKING:
    from app.models.learning_feedback import LearningFeedback
    from app.models.upload import Upload
    from app.models.video import Video


class Analytics(BaseModel):
    """Point-in-time metrics snapshot for a video."""

    __tablename__ = "analytics"
    __table_args__ = (
        CheckConstraint("views >= 0", name="ck_analytics_views_nonnegative"),
        CheckConstraint("likes >= 0", name="ck_analytics_likes_nonnegative"),
        CheckConstraint("comments >= 0", name="ck_analytics_comments_nonnegative"),
        CheckConstraint("shares >= 0", name="ck_analytics_shares_nonnegative"),
        CheckConstraint(
            "watch_time_seconds >= 0",
            name="ck_analytics_watch_time_nonnegative",
        ),
        CheckConstraint(
            "subscribers_gained >= 0",
            name="ck_analytics_subscribers_nonnegative",
        ),
        UniqueConstraint(
            "video_id",
            "platform",
            "snapshot_date",
            name="uq_analytics_video_platform_snapshot",
        ),
        Index("ix_analytics_video_snapshot", "video_id", "snapshot_date"),
        Index("ix_analytics_platform_snapshot", "platform", "snapshot_date"),
    )

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    platform: Mapped[UploadPlatform] = mapped_column(
        Enum(
            UploadPlatform,
            values_callable=enum_values,
            name="analytics_platform",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=UploadPlatform.YOUTUBE_SHORTS,
        server_default=UploadPlatform.YOUTUBE_SHORTS.value,
        index=True,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    views: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    likes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    comments: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    shares: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    watch_time_seconds: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    average_view_duration_seconds: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    retention_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    click_through_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    subscribers_gained: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    revenue_estimate: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
    )
    raw_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    video: Mapped["Video"] = relationship("Video", back_populates="analytics_records")
    upload: Mapped["Upload | None"] = relationship(
        "Upload",
        back_populates="analytics_records",
    )
    feedback: Mapped[list["LearningFeedback"]] = relationship(
        "LearningFeedback",
        back_populates="analytics",
        passive_deletes=True,
    )
