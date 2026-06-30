"""Pydantic schemas for visual generation output."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VisualGenerationResponse(BaseModel):
    """Public visual generation output contract."""

    scenes: list[dict[str, Any]] = Field(default_factory=list)
    prompts: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
