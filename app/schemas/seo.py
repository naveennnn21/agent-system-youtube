"""Pydantic schemas for YouTube SEO generation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SEOGenerationResponse(BaseModel):
    """Public SEO output contract."""

    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    hashtags: list[str] = Field(min_length=1, max_length=15)
    keywords: list[str] = Field(min_length=1, max_length=50)
