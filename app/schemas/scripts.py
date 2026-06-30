"""Pydantic schemas for script generation output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScriptGenerationResponse(BaseModel):
    """Public script generation output contract."""

    hook: str = Field(min_length=1)
    script: str = Field(min_length=1)
    cta: str = Field(min_length=1)
