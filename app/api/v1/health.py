"""
Health-check endpoints.

* ``GET /health``       — lightweight liveness probe.
* ``GET /health/ready``  — deep readiness probe (DB + Redis).

These endpoints are exempt from rate limiting so that load balancers
and orchestrators can always reach them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import RedisManager, redis_manager
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# ── Rate-limit exemption ────────────────────────────────────────────
# Health probes must never be blocked by rate limiting.
limiter = Limiter(key_func=get_remote_address)


# ── Liveness ─────────────────────────────────────────────────────────


@router.get("")
@limiter.exempt
async def health(request: Request) -> dict:
    """Lightweight liveness probe — always returns 200 if the process is up."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "youtube-shorts-ai-agent",
    }


# ── Readiness ────────────────────────────────────────────────────────


async def _check_database(session: AsyncSession) -> dict:
    """Execute a trivial query to verify database connectivity."""
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
        return {"status": "healthy", "latency_ms": None}
    except Exception as exc:
        logger.error("Database readiness check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


async def _check_redis(manager: RedisManager) -> dict:
    """Ping Redis and report status."""
    try:
        is_alive = await manager.ping()
        return {"status": "healthy" if is_alive else "unhealthy"}
    except Exception as exc:
        logger.error("Redis readiness check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


@router.get("/ready")
@limiter.exempt
async def readiness(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Deep readiness probe that checks every dependency.

    Returns an overall ``status`` of ``"healthy"`` only when **all**
    downstream services respond successfully.
    """
    db_status = await _check_database(session)
    redis_status = await _check_redis(redis_manager)

    checks = {
        "database": db_status,
        "redis": redis_status,
    }

    overall = (
        "healthy"
        if all(c.get("status") == "healthy" for c in checks.values())
        else "unhealthy"
    )

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
