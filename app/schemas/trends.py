"""Pydantic schemas for trend research output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrendTopicResponse(BaseModel):
    """Public trend topic output contract."""

    topic: str
    score: float = Field(ge=0, le=100)
    category: str
    keywords: list[str]
