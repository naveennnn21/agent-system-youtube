"""Script model."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import ScriptStatus, enum_values


class Script(BaseModel):
    """Script draft/revision generated for a topic or video."""

    __tablename__ = "scripts"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_scripts_version_positive"),
        CheckConstraint("prompt_tokens >= 0", name="ck_scripts_prompt_tokens_nonnegative"),
        CheckConstraint(
            "completion_tokens >= 0",
            name="ck_scripts_completion_tokens_nonnegative",
        ),
        CheckConstraint("total_tokens >= 0", name="ck_scripts_total_tokens_nonnegative"),
        UniqueConstraint("topic_id", "version", name="uq_scripts_topic_version"),
        Index("ix_scripts_topic_status", "topic_id", "status"),
        Index("ix_scripts_video_status", "video_id", "status"),
    )

    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ScriptStatus] = mapped_column(
        Enum(
            ScriptStatus,
            values_callable=enum_values,
            name="script_status",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=ScriptStatus.DRAFT,
        server_default=ScriptStatus.DRAFT.value,
        index=True,
    )
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    topic: Mapped["Topic | None"] = relationship("Topic", back_populates="scripts")
    video: Mapped["Video | None"] = relationship("Video", back_populates="scripts")
    feedback: Mapped[list["LearningFeedback"]] = relationship(
        "LearningFeedback",
        back_populates="script",
        passive_deletes=True,
    )
