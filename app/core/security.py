"""
app.core.security
~~~~~~~~~~~~~~~~~
Production security middleware.

Provides:
- ``SecurityHeadersMiddleware`` — adds security response headers.
- ``configure_security()`` — applies all security middleware to the FastAPI app.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that appends security hardening headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), midi=(), sync-xhr=(), "
            "accelerometer=(), gyroscope=(), magnetometer=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        return response


def configure_security(application: FastAPI) -> None:
    """Register all security middleware on the FastAPI application."""
    application.add_middleware(SecurityHeadersMiddleware)
    logger.debug("Security headers middleware registered.")
