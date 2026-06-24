"""
app.core.logging
~~~~~~~~~~~~~~~~~
Structured logging setup using *structlog*.

- **Development** → coloured, human-readable console output.
- **Production**  → JSON lines suitable for log aggregators (ELK, Datadog …).

Usage::

    from app.core.logging import setup_logging, get_logger

    setup_logging()           # call once at application startup
    logger = get_logger(__name__)
    logger.info("server_started", port=8000)
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure *structlog* and the stdlib ``logging`` root logger.

    Call this **once** during application startup (e.g. in the FastAPI
    lifespan handler) before any log messages are emitted.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    is_dev = settings.is_development

    # Shared processors applied to every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_dev:
        # Pretty, coloured output for local development
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=True,
        )
    else:
        # Machine-readable JSON for production log pipelines
        shared_processors.append(
            structlog.processors.format_exc_info,
        )
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Wire up the stdlib root logger so third-party libraries
    # (uvicorn, sqlalchemy, httpx …) also go through structlog.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Reduce noise from chatty libraries
    for noisy in ("httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named *structlog* bound logger.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.

    Returns
    -------
    structlog.stdlib.BoundLogger
        A logger instance bound to the given *name*.
    """
    return structlog.get_logger(name)
