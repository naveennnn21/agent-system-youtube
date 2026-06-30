"""Retry utilities for image providers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 4.0

    async def run(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        retryable: Callable[[Exception], bool],
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await operation()
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_attempts or not retryable(exc):
                    raise
                delay = min(
                    self.max_delay_seconds,
                    self.base_delay_seconds * (2 ** (attempt - 1)),
                )
                await asyncio.sleep(delay)
        raise last_error or RuntimeError("Retry operation failed unexpectedly.")
