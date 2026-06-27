"""
app.db.session
~~~~~~~~~~~~~~~
Async SQLAlchemy engine and session management.

Provides:
- ``async_engine``  — the shared async engine instance.
- ``AsyncSessionLocal`` — a session factory bound to the engine.
- ``get_db()``     — FastAPI dependency that yields a session per-request.
- ``init_db()``    — creates the engine (call on startup).
- ``close_db()``   — disposes the engine (call on shutdown).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Module-level singletons (initialised lazily via ``init_db()``)
# ---------------------------------------------------------------------------
async_engine = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Create the async engine and session factory.

    Call this once during application startup (e.g. inside the FastAPI
    lifespan context manager).
    """
    global async_engine, AsyncSessionLocal  # noqa: PLW0603

    settings = get_settings()

    engine_kwargs: dict[str, Any] = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
    }

    if settings.is_development:
        # NullPool does not accept queue-pool sizing arguments.
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
        )

    async_engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """Dispose of the async engine, releasing all pooled connections.

    Call this once during application shutdown.
    """
    global async_engine, AsyncSessionLocal  # noqa: PLW0603

    if async_engine is not None:
        await async_engine.dispose()
        async_engine = None
        AsyncSessionLocal = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a scoped async database session.

    The session is automatically closed when the request finishes. Usage::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database not initialised. Call init_db() during app startup."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
