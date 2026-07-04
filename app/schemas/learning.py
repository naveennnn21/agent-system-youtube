"""Pydantic schemas for learning recommendations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LearningAnalysisResponse(BaseModel):
    """Public learning analysis and recommendation output."""

    sample_count: int = Field(ge=0)
    winner_count: int = Field(ge=0)
    baseline_score: float = Field(ge=0)
    top_videos: list[dict[str, Any]]
    winning_hooks: list[dict[str, Any]]
    winning_topics: list[dict[str, Any]]
    winning_posting_times: list[dict[str, Any]]
    best_formats: list[dict[str, Any]]
    recommendations: dict[str, Any]
    model_version: str
    feedback_ids: list[str] = Field(default_factory=list)
