"""
Async Redis connection manager for the YouTube Shorts AI Agent.

Provides connection pooling, health checks, and a FastAPI-compatible
async dependency via `get_redis()`.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages an async Redis connection with pooling and lifecycle hooks.

    Usage::

        manager = RedisManager()
        await manager.connect()
        client = manager.get_client()
        await client.set("key", "value")
        await manager.disconnect()
    """

    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the connection pool and Redis client."""
        if self._pool is not None:
            logger.warning("RedisManager.connect() called but pool already exists.")
            return

        settings = get_settings()
        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
            encoding="utf-8",
        )
        self._client = Redis(connection_pool=self._pool)
        logger.info("Redis connection pool created (%s).", settings.REDIS_URL)

    async def disconnect(self) -> None:
        """Gracefully close the Redis client and drain the pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis client closed.")

        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
            logger.info("Redis connection pool closed.")

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_client(self) -> Redis:
        """Return the shared Redis client.

        Raises:
            RuntimeError: If ``connect()`` has not been called yet.
        """
        if self._client is None:
            raise RuntimeError(
                "Redis client is not initialised. Call RedisManager.connect() first."
            )
        return self._client

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """Return *True* if the Redis server responds to PING."""
        try:
            client = self.get_client()
            return await client.ping()
        except Exception:
            logger.exception("Redis health-check (PING) failed.")
            return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

redis_manager = RedisManager()


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency that yields the shared Redis client.

    Example::

        @router.get("/example")
        async def example(redis: Redis = Depends(get_redis)):
            await redis.set("hello", "world")
    """
    yield redis_manager.get_client()
