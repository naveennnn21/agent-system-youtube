"""Notification delivery for automation events."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationEvent:
    """Structured automation notification payload."""

    event_type: str
    status: str
    message: str
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "status": self.status,
            "message": self.message,
            "task_id": self.task_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class NotificationService:
    """Send automation notifications to an optional webhook."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def send(self, event: NotificationEvent) -> dict[str, Any]:
        payload = event.to_dict()
        logger.info("automation notification: %s", payload)

        if not self.settings.NOTIFICATIONS_ENABLED:
            return {"delivered": False, "reason": "notifications disabled", "event": payload}
        if not self.settings.NOTIFICATION_WEBHOOK_URL:
            return {"delivered": False, "reason": "webhook not configured", "event": payload}

        try:
            if self._client is not None:
                response = self._client.post(
                    self.settings.NOTIFICATION_WEBHOOK_URL,
                    json=payload,
                    timeout=self.settings.NOTIFICATION_WEBHOOK_TIMEOUT,
                )
            else:
                with httpx.Client(timeout=self.settings.NOTIFICATION_WEBHOOK_TIMEOUT) as client:
                    response = client.post(
                        self.settings.NOTIFICATION_WEBHOOK_URL,
                        json=payload,
                    )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("notification webhook delivery failed: %s", exc)
            return {"delivered": False, "reason": str(exc), "event": payload}

        return {
            "delivered": True,
            "status_code": response.status_code,
            "event": payload,
        }
