# Database Layer

This project uses PostgreSQL, SQLAlchemy 2.x async ORM, asyncpg, and Alembic.
The application owns the connection lifecycle in `app.db.session`, while schema
changes are applied through Alembic migrations in `alembic/versions`.

## Tables

### topics

Stores research ideas before they become scripts or videos.

Important columns:
- `title`, `slug`, `description`, `source`
- `keywords` as `varchar[]`
- `status`: `discovered`, `queued`, `approved`, `rejected`, `archived`
- `priority_score`, `trend_score`
- `metadata` as JSONB for provider-specific research data
- `discovered_at`, `approved_at`

Relationships:
- one topic can have many `scripts`
- one topic can have many `videos`
- one topic can have many `learning_feedback` records

### scripts

Stores generated script drafts and revisions.

Important columns:
- `topic_id`, `video_id`
- `version`
- `title`, `hook`, `body`, `cta`, `full_text`
- `status`: `draft`, `reviewed`, `approved`, `rejected`, `archived`
- `model_name`, token counts, `quality_score`, `review_notes`
- `metadata` as JSONB for prompt/model context

Constraints:
- `version > 0`
- token counts must be non-negative
- `(topic_id, version)` is unique

### videos

Stores short-form video artifacts.

Important columns:
- `topic_id`
- `title`, `description`
- `status`: `planned`, `rendering`, `rendered`, `uploading`, `published`, `failed`, `archived`
- `duration_seconds`, `language`, `aspect_ratio`
- `file_path`, `thumbnail_path`
- `metadata` as JSONB
- `scheduled_at`, `published_at`

Constraints:
- `duration_seconds` must be positive when present

### uploads

Stores attempts to upload rendered videos to external platforms.

Important columns:
- `video_id`
- `platform`: currently `youtube_shorts`
- `external_video_id`, `upload_url`
- `status`: `pending`, `uploading`, `succeeded`, `failed`, `retrying`
- `privacy_status`
- `request_payload`, `response_payload` as JSONB
- `error_message`, `started_at`, `uploaded_at`

Constraints:
- `(platform, external_video_id)` is unique

### analytics

Stores point-in-time metric snapshots.

Important columns:
- `video_id`, `upload_id`
- `platform`
- `snapshot_date`
- `views`, `likes`, `comments`, `shares`
- `watch_time_seconds`, `average_view_duration_seconds`
- `retention_rate`, `click_through_rate`
- `subscribers_gained`, `revenue_estimate`
- `raw_metrics` as JSONB

Constraints:
- count fields must be non-negative
- `(video_id, platform, snapshot_date)` is unique

### learning_feedback

Stores learning signals from content quality review, audience response, and
analytics results.

Important columns:
- optional links to `video_id`, `topic_id`, `script_id`, `analytics_id`
- `feedback_type`: `performance`, `quality`, `audience`, `system`
- `signal`, `score`, `notes`
- `recommendations` as JSONB
- `applied`, `model_version`, `reviewed_at`

## Model Files

- `app/models/topic.py`
- `app/models/script.py`
- `app/models/video.py`
- `app/models/upload.py`
- `app/models/analytics.py`
- `app/models/learning_feedback.py`
- `app/models/enums.py`

Each model inherits from `BaseModel`, which provides:
- `id` as UUID primary key
- `created_at`
- `updated_at`

## Repository Layer

Repositories live in `app/repositories`.

Base CRUD operations are implemented by `AsyncRepository`:
- `get(id)`
- `list(offset=0, limit=100, filters=(), order_by=None)`
- `count(filters=())`
- `exists(id)`
- `create(data=None, **values)`
- `update(instance, data=None, **values)`
- `update_by_id(id, data=None, **values)`
- `delete(id)`

Domain repositories add targeted queries:
- `TopicsRepository`
- `ScriptsRepository`
- `VideosRepository`
- `UploadsRepository`
- `AnalyticsRepository`
- `LearningFeedbackRepository`

Example:

```python
from app.repositories import TopicsRepository
from app.models.enums import TopicStatus


async def approve_topic(db, topic_id):
    repo = TopicsRepository(db)
    topic = await repo.update_by_id(topic_id, status=TopicStatus.APPROVED)
    return topic
```

Repositories flush and refresh rows but do not commit. The FastAPI `get_db`
dependency commits successful requests and rolls back failed requests.

## Migrations

Apply migrations:

```bash
docker compose exec app alembic upgrade head
```

Create a new migration after model changes:

```bash
docker compose exec app alembic revision --autogenerate -m "describe change"
```

Rollback one revision:

```bash
docker compose exec app alembic downgrade -1
```

## Operational Notes

- PostgreSQL `pgcrypto` is enabled by the first migration for `gen_random_uuid()`.
- JSONB columns store provider payloads without forcing schema changes for every
  YouTube or AI metadata change.
- Delete behavior is conservative:
  - deleting a video cascades uploads and analytics
  - deleting a topic keeps videos/scripts but nulls their `topic_id`
  - feedback links are nullable so historical learning can remain available
