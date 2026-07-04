"""
Main API router — aggregates all versioned sub-routers.

All API endpoints are mounted here and included in the FastAPI app
via ``app.include_router(api_router)``.
"""

from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.automation import router as automation_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router

api_router = APIRouter()

# ── v1 routes ────────────────────────────────────────────────────────
api_router.include_router(
    health_router,
    prefix="/v1",
    tags=["health"],
)
api_router.include_router(
    analytics_router,
    prefix="/v1",
    tags=["analytics"],
)
api_router.include_router(
    automation_router,
    prefix="/v1",
    tags=["automation"],
)
api_router.include_router(
    dashboard_router,
    prefix="/v1",
    tags=["dashboard"],
)
