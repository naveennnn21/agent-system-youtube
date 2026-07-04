"""Celery application configuration for the automation layer."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "youtube_shorts_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.automation.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=settings.CELERY_ENABLE_UTC,
    result_expires=60 * 60 * 24 * 7,
    result_serializer="json",
    task_acks_late=True,
    task_default_exchange="youtube_shorts_agent",
    task_default_exchange_type="direct",
    task_default_queue=settings.AUTOMATION_AUTOSTART_QUEUE,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_EAGER_PROPAGATES,
    timezone=settings.CELERY_TIMEZONE,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
)

exchange = Exchange("youtube_shorts_agent", type="direct")
celery_app.conf.task_queues = (
    Queue(settings.AUTOMATION_AUTOSTART_QUEUE, exchange, routing_key=settings.AUTOMATION_AUTOSTART_QUEUE),
    Queue(settings.AUTOMATION_SHORTS_QUEUE, exchange, routing_key=settings.AUTOMATION_SHORTS_QUEUE),
    Queue(settings.AUTOMATION_ANALYTICS_QUEUE, exchange, routing_key=settings.AUTOMATION_ANALYTICS_QUEUE),
    Queue(settings.AUTOMATION_NOTIFICATIONS_QUEUE, exchange, routing_key=settings.AUTOMATION_NOTIFICATIONS_QUEUE),
)

celery_app.conf.task_routes = {
    "app.automation.tasks.dispatch_daily_shorts": {
        "queue": settings.AUTOMATION_AUTOSTART_QUEUE,
        "routing_key": settings.AUTOMATION_AUTOSTART_QUEUE,
    },
    "app.automation.tasks.generate_short": {
        "queue": settings.AUTOMATION_SHORTS_QUEUE,
        "routing_key": settings.AUTOMATION_SHORTS_QUEUE,
    },
    "app.automation.tasks.collect_analytics": {
        "queue": settings.AUTOMATION_ANALYTICS_QUEUE,
        "routing_key": settings.AUTOMATION_ANALYTICS_QUEUE,
    },
    "app.automation.tasks.run_learning": {
        "queue": settings.AUTOMATION_ANALYTICS_QUEUE,
        "routing_key": settings.AUTOMATION_ANALYTICS_QUEUE,
    },
    "app.automation.tasks.send_notification": {
        "queue": settings.AUTOMATION_NOTIFICATIONS_QUEUE,
        "routing_key": settings.AUTOMATION_NOTIFICATIONS_QUEUE,
    },
}

celery_app.conf.beat_schedule = {
    "generate-three-shorts-daily": {
        "task": "app.automation.tasks.dispatch_daily_shorts",
        "schedule": crontab(
            hour=settings.AUTOMATION_DAILY_CRON_HOUR,
            minute=settings.AUTOMATION_DAILY_CRON_MINUTE,
        ),
        "options": {"queue": settings.AUTOMATION_AUTOSTART_QUEUE},
    },
    "collect-youtube-analytics-daily": {
        "task": "app.automation.tasks.collect_analytics",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": settings.AUTOMATION_ANALYTICS_QUEUE},
    },
    "run-learning-daily": {
        "task": "app.automation.tasks.run_learning",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": settings.AUTOMATION_ANALYTICS_QUEUE},
    },
}
