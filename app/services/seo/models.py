"""Data models for YouTube SEO metadata generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SEOGenerationRequest:
    """Content context used to produce searchable, clickable metadata."""

    topic: str
    script: str | dict[str, str]
    category: str = "general"
    seed_keywords: list[str] = field(default_factory=list)
    audience: str = "curious general viewers"
    language: str = "English"
    channel_name: str = ""
    research_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SEOMetadata:
    """Public SEO output contract."""

    title: str
    description: str
    hashtags: list[str]
    keywords: list[str]

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "title": self.title,
            "description": self.description,
            "hashtags": list(self.hashtags),
            "keywords": list(self.keywords),
        }


@dataclass(slots=True)
class SEOEvaluation:
    """Deterministic quality report for generated metadata."""

    ctr_score: float
    discoverability_score: float
    description_score: float
    overall_score: float
    is_valid: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
