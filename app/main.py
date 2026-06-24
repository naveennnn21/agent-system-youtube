"""
FastAPI application entry point for the YouTube Shorts AI Agent.

Boots the app, initialises database and Redis connections via a
lifespan context manager, and mounts all API routers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.redis import redis_manager
from app.db.session import init_db, close_db

logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hook.

    * **Startup** — configure logging, initialise DB engine and Redis.
    * **Shutdown** — dispose of the engine pool and disconnect Redis.
    """
    setup_logging()
    logger.info("Starting up — initialising connections …")

    # Database
    await init_db()
    logger.info("Database engine ready.")

    # Redis
    await redis_manager.connect()
    logger.info("Redis connected.")

    yield  # ← application serves requests here

    # Shutdown
    logger.info("Shutting down — closing connections …")
    await redis_manager.disconnect()
    await close_db()
    logger.info("All connections closed.")


# ── App factory ───────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title="YouTube Shorts AI Agent",
        description=(
            "Autonomous AI agent system that researches, scripts, "
            "and produces YouTube Shorts content using LangGraph + LangChain."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────
    application.include_router(api_router, prefix="/api")

    # ── Root endpoint ─────────────────────────────────────────────

    @application.get("/", tags=["root"])
    async def root() -> dict:
        """Welcome message and quick reference links."""
        return {
            "message": "Welcome to the YouTube Shorts AI Agent API 🎬",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    # ── Exception handlers ────────────────────────────────────────

    @application.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @application.exception_handler(PermissionError)
    async def permission_error_handler(
        request: Request, exc: PermissionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)},
        )

    @application.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    return application


# Application instance used by uvicorn / gunicorn
app = create_app()
