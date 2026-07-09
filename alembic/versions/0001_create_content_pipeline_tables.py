"""create content pipeline tables

Revision ID: 0001_content_pipeline
Revises:
Create Date: 2026-06-27 10:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_content_pipeline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


topic_status = sa.Enum(
    "discovered",
    "queued",
    "approved",
    "rejected",
    "archived",
    name="topic_status",
    native_enum=False,
    create_constraint=True,
    length=32,
)
script_status = sa.Enum(
    "draft",
    "reviewed",
    "approved",
    "rejected",
    "archived",
    name="script_status",
    native_enum=False,
    create_constraint=True,
    length=32,
)
video_status = sa.Enum(
    "planned",
    "rendering",
    "rendered",
    "uploading",
    "published",
    "failed",
    "archived",
    name="video_status",
    native_enum=False,
    create_constraint=True,
    length=32,
)
upload_status = sa.Enum(
    "pending",
    "uploading",
    "succeeded",
    "failed",
    "retrying",
    name="upload_status",
    native_enum=False,
    create_constraint=True,
    length=32,
)
upload_platform = sa.Enum(
    "youtube_shorts",
    name="upload_platform",
    native_enum=False,
    create_constraint=True,
    length=32,
)
analytics_platform = sa.Enum(
    "youtube_shorts",
    name="analytics_platform",
    native_enum=False,
    create_constraint=True,
    length=32,
)
feedback_type = sa.Enum(
    "performance",
    "quality",
    "audience",
    "system",
    name="feedback_type",
    native_enum=False,
    create_constraint=True,
    length=32,
)


def uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "topics",
        uuid_pk(),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=280), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.String(length=128)),
            server_default=sa.text("ARRAY[]::varchar[]"),
            nullable=False,
        ),
        sa.Column(
            "status",
            topic_status,
            server_default="discovered",
            nullable=False,
        ),
        sa.Column(
            "priority_score",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "trend_score",
            sa.Numeric(precision=8, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_topics_title", "topics", ["title"])
    op.create_index("ix_topics_source", "topics", ["source"])
    op.create_index("ix_topics_status", "topics", ["status"])
    op.create_index(
        "ix_topics_status_priority",
        "topics",
        ["status", "priority_score"],
    )
    op.create_index(
        "ix_topics_source_discovered_at",
        "topics",
        ["source", "discovered_at"],
    )

    op.create_table(
        "videos",
        uuid_pk(),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", video_status, server_default="planned", nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "language", sa.String(length=16), server_default="en", nullable=False
        ),
        sa.Column(
            "aspect_ratio",
            sa.String(length=16),
            server_default="9:16",
            nullable=False,
        ),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=1024), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_videos_duration_positive",
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_videos_topic_id", "videos", ["topic_id"])
    op.create_index("ix_videos_title", "videos", ["title"])
    op.create_index("ix_videos_status", "videos", ["status"])
    op.create_index("ix_videos_topic_status", "videos", ["topic_id", "status"])
    op.create_index("ix_videos_published_at", "videos", ["published_at"])

    op.create_table(
        "scripts",
        uuid_pk(),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("hook", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("cta", sa.Text(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("status", script_status, server_default="draft", nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quality_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamps(),
        sa.CheckConstraint("version > 0", name="ck_scripts_version_positive"),
        sa.CheckConstraint(
            "prompt_tokens >= 0",
            name="ck_scripts_prompt_tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "completion_tokens >= 0",
            name="ck_scripts_completion_tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "total_tokens >= 0",
            name="ck_scripts_total_tokens_nonnegative",
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_id", "version", name="uq_scripts_topic_version"),
    )
    op.create_index("ix_scripts_topic_id", "scripts", ["topic_id"])
    op.create_index("ix_scripts_video_id", "scripts", ["video_id"])
    op.create_index("ix_scripts_status", "scripts", ["status"])
    op.create_index("ix_scripts_topic_status", "scripts", ["topic_id", "status"])
    op.create_index("ix_scripts_video_status", "scripts", ["video_id", "status"])

    op.create_table(
        "uploads",
        uuid_pk(),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            upload_platform,
            server_default="youtube_shorts",
            nullable=False,
        ),
        sa.Column("external_video_id", sa.String(length=255), nullable=True),
        sa.Column("upload_url", sa.String(length=2048), nullable=True),
        sa.Column("status", upload_status, server_default="pending", nullable=False),
        sa.Column(
            "privacy_status",
            sa.String(length=32),
            server_default="private",
            nullable=False,
        ),
        sa.Column(
            "request_payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "response_payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "platform",
            "external_video_id",
            name="uq_uploads_platform_external_video_id",
        ),
    )
    op.create_index("ix_uploads_video_id", "uploads", ["video_id"])
    op.create_index("ix_uploads_platform", "uploads", ["platform"])
    op.create_index("ix_uploads_status", "uploads", ["status"])
    op.create_index("ix_uploads_video_status", "uploads", ["video_id", "status"])
    op.create_index("ix_uploads_platform_status", "uploads", ["platform", "status"])

    op.create_table(
        "analytics",
        uuid_pk(),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "platform",
            analytics_platform,
            server_default="youtube_shorts",
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("views", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("likes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("comments", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("shares", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "watch_time_seconds",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "average_view_duration_seconds",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column("retention_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "click_through_rate",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
        sa.Column(
            "subscribers_gained",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "revenue_estimate",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
        ),
        sa.Column(
            "raw_metrics",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamps(),
        sa.CheckConstraint("views >= 0", name="ck_analytics_views_nonnegative"),
        sa.CheckConstraint("likes >= 0", name="ck_analytics_likes_nonnegative"),
        sa.CheckConstraint(
            "comments >= 0",
            name="ck_analytics_comments_nonnegative",
        ),
        sa.CheckConstraint("shares >= 0", name="ck_analytics_shares_nonnegative"),
        sa.CheckConstraint(
            "watch_time_seconds >= 0",
            name="ck_analytics_watch_time_nonnegative",
        ),
        sa.CheckConstraint(
            "subscribers_gained >= 0",
            name="ck_analytics_subscribers_nonnegative",
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "video_id",
            "platform",
            "snapshot_date",
            name="uq_analytics_video_platform_snapshot",
        ),
    )
    op.create_index("ix_analytics_video_id", "analytics", ["video_id"])
    op.create_index("ix_analytics_upload_id", "analytics", ["upload_id"])
    op.create_index("ix_analytics_platform", "analytics", ["platform"])
    op.create_index("ix_analytics_snapshot_date", "analytics", ["snapshot_date"])
    op.create_index(
        "ix_analytics_video_snapshot",
        "analytics",
        ["video_id", "snapshot_date"],
    )
    op.create_index(
        "ix_analytics_platform_snapshot",
        "analytics",
        ["platform", "snapshot_date"],
    )

    op.create_table(
        "learning_feedback",
        uuid_pk(),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("script_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analytics_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "feedback_type",
            feedback_type,
            server_default="performance",
            nullable=False,
        ),
        sa.Column("signal", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "recommendations",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("applied", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["analytics_id"],
            ["analytics.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_feedback_video_id", "learning_feedback", ["video_id"])
    op.create_index("ix_learning_feedback_topic_id", "learning_feedback", ["topic_id"])
    op.create_index(
        "ix_learning_feedback_script_id", "learning_feedback", ["script_id"]
    )
    op.create_index(
        "ix_learning_feedback_analytics_id",
        "learning_feedback",
        ["analytics_id"],
    )
    op.create_index(
        "ix_learning_feedback_feedback_type",
        "learning_feedback",
        ["feedback_type"],
    )
    op.create_index("ix_learning_feedback_applied", "learning_feedback", ["applied"])
    op.create_index(
        "ix_learning_feedback_video_type",
        "learning_feedback",
        ["video_id", "feedback_type"],
    )
    op.create_index(
        "ix_learning_feedback_topic_type",
        "learning_feedback",
        ["topic_id", "feedback_type"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_learning_feedback_topic_type", table_name="learning_feedback")
    op.drop_index("ix_learning_feedback_video_type", table_name="learning_feedback")
    op.drop_index("ix_learning_feedback_applied", table_name="learning_feedback")
    op.drop_index("ix_learning_feedback_feedback_type", table_name="learning_feedback")
    op.drop_index("ix_learning_feedback_analytics_id", table_name="learning_feedback")
    op.drop_index("ix_learning_feedback_script_id", table_name="learning_feedback")
    op.drop_index("ix_learning_feedback_topic_id", table_name="learning_feedback")
    op.drop_index("ix_learning_feedback_video_id", table_name="learning_feedback")
    op.drop_table("learning_feedback")

    op.drop_index("ix_analytics_platform_snapshot", table_name="analytics")
    op.drop_index("ix_analytics_video_snapshot", table_name="analytics")
    op.drop_index("ix_analytics_snapshot_date", table_name="analytics")
    op.drop_index("ix_analytics_platform", table_name="analytics")
    op.drop_index("ix_analytics_upload_id", table_name="analytics")
    op.drop_index("ix_analytics_video_id", table_name="analytics")
    op.drop_table("analytics")

    op.drop_index("ix_uploads_platform_status", table_name="uploads")
    op.drop_index("ix_uploads_video_status", table_name="uploads")
    op.drop_index("ix_uploads_status", table_name="uploads")
    op.drop_index("ix_uploads_platform", table_name="uploads")
    op.drop_index("ix_uploads_video_id", table_name="uploads")
    op.drop_table("uploads")

    op.drop_index("ix_scripts_video_status", table_name="scripts")
    op.drop_index("ix_scripts_topic_status", table_name="scripts")
    op.drop_index("ix_scripts_status", table_name="scripts")
    op.drop_index("ix_scripts_video_id", table_name="scripts")
    op.drop_index("ix_scripts_topic_id", table_name="scripts")
    op.drop_table("scripts")

    op.drop_index("ix_videos_published_at", table_name="videos")
    op.drop_index("ix_videos_topic_status", table_name="videos")
    op.drop_index("ix_videos_status", table_name="videos")
    op.drop_index("ix_videos_title", table_name="videos")
    op.drop_index("ix_videos_topic_id", table_name="videos")
    op.drop_table("videos")

    op.drop_index("ix_topics_source_discovered_at", table_name="topics")
    op.drop_index("ix_topics_status_priority", table_name="topics")
    op.drop_index("ix_topics_status", table_name="topics")
    op.drop_index("ix_topics_source", table_name="topics")
    op.drop_index("ix_topics_title", table_name="topics")
    op.drop_table("topics")
