"""Data models for content learning and recommendations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class LearningAnalysisRequest:
    """Configuration for a learning run."""

    lookback_days: int = 90
    top_n: int = 5
    max_samples: int = 500
    min_views: int = 100
    store_results: bool = True
    model_version: str = "learning-agent-v1"


@dataclass(slots=True)
class ContentPerformanceSample:
    """One video plus the content context needed for learning."""

    video_id: uuid.UUID | None
    topic_id: uuid.UUID | None
    script_id: uuid.UUID | None
    analytics_id: uuid.UUID | None
    title: str
    topic: str
    hook: str
    keywords: list[str]
    published_at: datetime | None
    scheduled_at: datetime | None
    duration_seconds: int | None
    aspect_ratio: str
    format_label: str
    metrics: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": str(self.video_id) if self.video_id else None,
            "topic_id": str(self.topic_id) if self.topic_id else None,
            "script_id": str(self.script_id) if self.script_id else None,
            "analytics_id": str(self.analytics_id) if self.analytics_id else None,
            "title": self.title,
            "topic": self.topic,
            "hook": self.hook,
            "keywords": self.keywords,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "duration_seconds": self.duration_seconds,
            "aspect_ratio": self.aspect_ratio,
            "format_label": self.format_label,
            "metrics": self.metrics,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ScoredContentSample:
    """Performance sample with an aggregate score."""

    sample: ContentPerformanceSample
    score: float

    def to_dict(self) -> dict[str, Any]:
        payload = self.sample.to_dict()
        payload["score"] = self.score
        return payload


@dataclass(slots=True)
class WinningSignal:
    """A repeated or high-performing content signal."""

    signal: str
    value: str
    score: float
    count: int
    evidence: list[dict[str, Any]] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "value": self.value,
            "score": self.score,
            "count": self.count,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass(slots=True)
class ContentRecommendations:
    """Actionable strategy for improving future content."""

    next_topics: list[dict[str, Any]]
    hook_templates: list[dict[str, Any]]
    posting_schedule: list[dict[str, Any]]
    format_defaults: dict[str, Any]
    generation_hints: dict[str, Any]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "next_topics": self.next_topics,
            "hook_templates": self.hook_templates,
            "posting_schedule": self.posting_schedule,
            "format_defaults": self.format_defaults,
            "generation_hints": self.generation_hints,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class LearningAnalysisResult:
    """Full output of a learning run."""

    sample_count: int
    winner_count: int
    baseline_score: float
    top_videos: list[ScoredContentSample]
    winning_hooks: list[WinningSignal]
    winning_topics: list[WinningSignal]
    winning_posting_times: list[WinningSignal]
    best_formats: list[WinningSignal]
    recommendations: ContentRecommendations
    model_version: str
    feedback_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "winner_count": self.winner_count,
            "baseline_score": self.baseline_score,
            "top_videos": [video.to_dict() for video in self.top_videos],
            "winning_hooks": [hook.to_dict() for hook in self.winning_hooks],
            "winning_topics": [topic.to_dict() for topic in self.winning_topics],
            "winning_posting_times": [time.to_dict() for time in self.winning_posting_times],
            "best_formats": [fmt.to_dict() for fmt in self.best_formats],
            "recommendations": self.recommendations.to_dict(),
            "model_version": self.model_version,
            "feedback_ids": self.feedback_ids,
        }
