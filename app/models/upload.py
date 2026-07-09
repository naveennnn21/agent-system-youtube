"""Upload model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import UploadPlatform, UploadStatus, enum_values

if TYPE_CHECKING:
    from app.models.analytics import Analytics
    from app.models.video import Video


class Upload(BaseModel):
    """Attempt to upload a rendered video to an external platform."""

    __tablename__ = "uploads"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "external_video_id",
            name="uq_uploads_platform_external_video_id",
        ),
        Index("ix_uploads_video_status", "video_id", "status"),
        Index("ix_uploads_platform_status", "platform", "status"),
    )

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[UploadPlatform] = mapped_column(
        Enum(
            UploadPlatform,
            values_callable=enum_values,
            name="upload_platform",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=UploadPlatform.YOUTUBE_SHORTS,
        server_default=UploadPlatform.YOUTUBE_SHORTS.value,
        index=True,
    )
    external_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upload_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[UploadStatus] = mapped_column(
        Enum(
            UploadStatus,
            values_callable=enum_values,
            name="upload_status",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=UploadStatus.PENDING,
        server_default=UploadStatus.PENDING.value,
        index=True,
    )
    privacy_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="private",
        server_default="private",
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    response_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    video: Mapped["Video"] = relationship("Video", back_populates="uploads")
    analytics_records: Mapped[list["Analytics"]] = relationship(
        "Analytics",
        back_populates="upload",
        passive_deletes=True,
    )
