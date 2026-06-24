"""
Main API router — aggregates all versioned sub-routers.

All API endpoints are mounted here and included in the FastAPI app
via ``app.include_router(api_router)``.
"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_router = APIRouter()

# ── v1 routes ────────────────────────────────────────────────────────
api_router.include_router(
    health_router,
    prefix="/v1",
    tags=["health"],
)
