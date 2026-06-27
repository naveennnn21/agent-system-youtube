"""Learning feedback model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import FeedbackType, enum_values


class LearningFeedback(BaseModel):
    """Actionable learning signal produced from content and analytics."""

    __tablename__ = "learning_feedback"
    __table_args__ = (
        Index("ix_learning_feedback_video_type", "video_id", "feedback_type"),
        Index("ix_learning_feedback_topic_type", "topic_id", "feedback_type"),
        Index("ix_learning_feedback_applied", "applied"),
    )

    video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    script_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    analytics_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analytics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feedback_type: Mapped[FeedbackType] = mapped_column(
        Enum(
            FeedbackType,
            values_callable=enum_values,
            name="feedback_type",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=FeedbackType.PERFORMANCE,
        server_default=FeedbackType.PERFORMANCE.value,
        index=True,
    )
    signal: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    applied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    video: Mapped["Video | None"] = relationship("Video", back_populates="feedback")
    topic: Mapped["Topic | None"] = relationship("Topic", back_populates="feedback")
    script: Mapped["Script | None"] = relationship("Script", back_populates="feedback")
    analytics: Mapped["Analytics | None"] = relationship(
        "Analytics",
        back_populates="feedback",
    )
