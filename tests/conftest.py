"""
Pytest fixtures shared across the entire test suite.

Provides:
* ``client``  — sync ``TestClient`` for integration tests.
* ``async_session`` — async SQLAlchemy session backed by a test DB.
* ``mock_redis`` — patched Redis client that avoids real connections.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


# ── Event-loop fixture (session-scoped) ──────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── FastAPI TestClient ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Synchronous ``TestClient`` that exercises the full ASGI stack."""
    with TestClient(app) as tc:
        yield tc


# ── Async database session ───────────────────────────────────────────

_settings = get_settings()

TEST_DATABASE_URL = _settings.DATABASE_URL  # Override for a dedicated test DB if desired.

_test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

_TestSessionLocal = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session that rolls back after each test."""
    async with _test_engine.begin() as conn:
        session = _TestSessionLocal(bind=conn)
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(autouse=True)
def _override_db_dependency(request):
    """Swap the production DB dependency with the test session."""
    if request.node.get_closest_marker("no_db"):
        yield
        return

    async_session = request.getfixturevalue("async_session")

    async def _get_test_session():
        yield async_session

    app.dependency_overrides[get_db] = _get_test_session
    yield
    app.dependency_overrides.pop(get_db, None)


# ── Redis mock ───────────────────────────────────────────────────────


@pytest.fixture
def mock_redis() -> MagicMock:
    """Return a ``MagicMock`` that stands in for the async Redis client.

    Common commands (``get``, ``set``, ``ping``, ``delete``) are
    pre-configured as ``AsyncMock`` instances so they can be awaited.
    """
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock()
    return client
