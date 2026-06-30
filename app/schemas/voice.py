"""Pydantic schemas for voice generation output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceGenerationResponse(BaseModel):
    """Public voice generation output contract."""

    audio_path: str = Field(min_length=1)
    duration: float = Field(ge=0)
