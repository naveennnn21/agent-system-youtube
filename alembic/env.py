"""
Alembic environment configuration — async PostgreSQL migrations.

This module is executed by Alembic whenever you run a migration command.
It supports two modes:

* **Offline** — generates SQL scripts without connecting to the database.
* **Online (async)** — runs migrations directly against PostgreSQL using
  the async engine from ``app.db.session``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings

# Import Base so Alembic can detect models for --autogenerate.
from app.db.base import Base  # noqa: F401 — side-effect import

# ── Alembic Config object ────────────────────────────────────────────

config = context.config

# Override the sqlalchemy.url with the async URL from settings.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from the alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData object used for 'autogenerate' support.
target_metadata = Base.metadata


# ── Offline migrations ───────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL (no Engine needed) and
    emits ``BEGIN`` / ``COMMIT`` / DDL to a script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online (async) migrations ────────────────────────────────────────


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a live connection (called inside the async wrapper)."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine, connect, and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode — delegates to the async runner."""
    asyncio.run(run_async_migrations())


# ── Entrypoint ────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
