"""Data structures for trend research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TrendSignal:
    """Raw trend signal collected from an external source."""

    source: str
    title: str
    category: str = "general"
    keywords: list[str] = field(default_factory=list)
    engagement: float = 0.0
    url: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrendTopic:
    """Scored trend topic returned by the research agent."""

    topic: str
    score: float
    category: str
    keywords: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return the public output contract."""
        return {
            "topic": self.topic,
            "score": self.score,
            "category": self.category,
            "keywords": self.keywords,
        }
