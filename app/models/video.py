"""Video model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import VideoStatus, enum_values

if TYPE_CHECKING:
    from app.models.analytics import Analytics
    from app.models.learning_feedback import LearningFeedback
    from app.models.script import Script
    from app.models.topic import Topic
    from app.models.upload import Upload


class Video(BaseModel):
    """Short-form video artifact produced from a topic and script."""

    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_videos_duration_positive",
        ),
        Index("ix_videos_topic_status", "topic_id", "status"),
        Index("ix_videos_published_at", "published_at"),
    )

    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VideoStatus] = mapped_column(
        Enum(
            VideoStatus,
            values_callable=enum_values,
            name="video_status",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=VideoStatus.PLANNED,
        server_default=VideoStatus.PLANNED.value,
        index=True,
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en",
        server_default="en",
    )
    aspect_ratio: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="9:16",
        server_default="9:16",
    )
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    topic: Mapped["Topic | None"] = relationship("Topic", back_populates="videos")
    scripts: Mapped[list["Script"]] = relationship(
        "Script",
        back_populates="video",
        passive_deletes=True,
    )
    uploads: Mapped[list["Upload"]] = relationship(
        "Upload",
        back_populates="video",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    analytics_records: Mapped[list["Analytics"]] = relationship(
        "Analytics",
        back_populates="video",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedback: Mapped[list["LearningFeedback"]] = relationship(
        "LearningFeedback",
        back_populates="video",
        passive_deletes=True,
    )
