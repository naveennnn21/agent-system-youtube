"""Pydantic schemas for YouTube upload output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class YouTubeUploadResponse(BaseModel):
    """Public YouTube upload output contract."""

    video_id: str = Field(min_length=1)
    video_url: str = Field(min_length=1)
    upload_status: str = Field(min_length=1)
