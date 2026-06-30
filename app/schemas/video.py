"""Pydantic schemas for video editing output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VideoEditingResponse(BaseModel):
    """Public video editing output contract."""

    video_path: str = Field(min_length=1)
    width: int = Field(default=1080)
    height: int = Field(default=1920)
    duration: float = Field(ge=0)
