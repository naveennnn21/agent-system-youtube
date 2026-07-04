# Automation Layer

The automation layer uses Celery, Redis, and Celery Beat to run production
workflows outside the FastAPI request cycle.

## Services

Docker Compose now defines:

- `app`: FastAPI API server
- `celery_worker`: Celery worker listening on `automation`, `shorts`,
  `analytics`, and `notifications`
- `celery_beat`: cron scheduler for recurring jobs
- `redis`: broker and result backend
- `db`: PostgreSQL

## Daily Shorts

Celery Beat schedules `app.automation.tasks.dispatch_daily_shorts` every day at:

- `AUTOMATION_DAILY_CRON_HOUR`
- `AUTOMATION_DAILY_CRON_MINUTE`

That dispatcher enqueues `AUTOMATION_DAILY_SHORTS_COUNT` independent
`generate_short` jobs, spaced by `AUTOMATION_SHORT_SPACING_MINUTES`. The default
is three Shorts per day.

## Queues

Default queues:

- `automation`: dispatch/control tasks
- `shorts`: full Short generation workflow jobs
- `analytics`: analytics collection and learning jobs
- `notifications`: webhook/log notifications

## Retry Behavior

Production tasks use Celery retry settings:

- `CELERY_TASK_MAX_RETRIES`
- `CELERY_TASK_RETRY_BACKOFF`
- `CELERY_TASK_RETRY_BACKOFF_MAX`

If the LangGraph workflow returns `workflow_status=failed`, the Celery task raises
an error so the worker retries it according to policy.

## Notifications

Notifications are always logged. If `NOTIFICATION_WEBHOOK_URL` is configured and
`NOTIFICATIONS_ENABLED=true`, events are also posted as JSON webhooks.

## APIs

- `POST /api/v1/automation/shorts`
- `POST /api/v1/automation/daily-shorts`
- `POST /api/v1/automation/analytics`
- `POST /api/v1/automation/learning`
- `GET /api/v1/automation/queues`
- `GET /api/v1/automation/tasks/{task_id}`
- `POST /api/v1/automation/tasks/{task_id}/revoke`
- `DELETE /api/v1/automation/queues/{queue_name}`
