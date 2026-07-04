"""Automation layer for scheduled and queued production jobs."""

from app.automation.celery_app import celery_app

__all__ = ["celery_app"]
