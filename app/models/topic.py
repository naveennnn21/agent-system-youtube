"""Topic model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import TopicStatus, enum_values

if TYPE_CHECKING:
    from app.models.learning_feedback import LearningFeedback
    from app.models.script import Script
    from app.models.video import Video


class Topic(BaseModel):
    """Research topic that can produce one or more scripts and videos."""

    __tablename__ = "topics"
    __table_args__ = (
        Index("ix_topics_status_priority", "status", "priority_score"),
        Index("ix_topics_source_discovered_at", "source", "discovered_at"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str | None] = mapped_column(String(280), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String(128)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
    )
    status: Mapped[TopicStatus] = mapped_column(
        Enum(
            TopicStatus,
            values_callable=enum_values,
            name="topic_status",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=TopicStatus.DISCOVERED,
        server_default=TopicStatus.DISCOVERED.value,
        index=True,
    )
    priority_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    trend_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    videos: Mapped[list["Video"]] = relationship(
        "Video",
        back_populates="topic",
        passive_deletes=True,
    )
    scripts: Mapped[list["Script"]] = relationship(
        "Script",
        back_populates="topic",
        passive_deletes=True,
    )
    feedback: Mapped[list["LearningFeedback"]] = relationship(
        "LearningFeedback",
        back_populates="topic",
        passive_deletes=True,
    )
